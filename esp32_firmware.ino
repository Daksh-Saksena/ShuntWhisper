#include <Arduino.h>
#include <driver/i2s.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include "esp_dsp.h"
#include "shunt_model.h"
#define I2S_WS 15
#define I2S_SD 13
#define I2S_SCK 2
#define I2S_PORT I2S_NUM_0
#define BLE_SERVER_NAME "ShuntWhisper_#HW8492"
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHAR_TELEMETRY_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHAR_INFERENCE_UUID "d99b1a5a-8b15-4df3-a1bc-7f41f02c6114"
BLECharacteristic *pCharTelemetry;
BLECharacteristic *pCharInference;
bool deviceConnected = false;
#define SAMPLE_RATE 16000
#define FFT_SAMPLES 1024
#define ML_FEATURES 3
float fft_buffer[FFT_SAMPLES * 2];
float mfcc_features[ML_FEATURES];
float z_score_loss = 0.0f;
float baseline_mean[ML_FEATURES] = {0.45, 0.22, 0.18};
float baseline_std[ML_FEATURES] = {0.05, 0.08, 0.03};
TaskHandle_t InferenceTask;
class ServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("Dashboard Connected via WebBLE");
    }
    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        pServer->startAdvertising();
        Serial.println("Dashboard Disconnected. Awaiting reconnect...");
    }
};
void setupI2S() {
    const i2s_config_t i2s_config = {
        .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = i2s_bits_per_sample_t(16),
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = 0,
        .dma_buf_count = 8,
        .dma_buf_len = FFT_SAMPLES,
        .use_apll = false
    };
    const i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = -1,
        .data_in_num = I2S_SD
    };
    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
}
void setupBLE() {
    BLEDevice::init(BLE_SERVER_NAME);
    BLEServer *pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    BLEService *pService = pServer->createService(SERVICE_UUID);
    pCharTelemetry = pService->createCharacteristic(
        CHAR_TELEMETRY_UUID,
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pCharTelemetry->addDescriptor(new BLE2902());
    pCharInference = pService->createCharacteristic(
        CHAR_INFERENCE_UUID,
        BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ
    );
    pCharInference->addDescriptor(new BLE2902());
    pService->start();
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    BLEDevice::startAdvertising();
}
void coreInferenceTask(void * pvParameters) {
    dsps_fft2r_init_fc32(NULL, FFT_SAMPLES);
    for(;;) {
        size_t bytes_read = 0;
        int16_t i2s_data[FFT_SAMPLES];
        i2s_read(I2S_PORT, &i2s_data, sizeof(i2s_data), &bytes_read, portMAX_DELAY);
        float rms = 0.0f;
        int zero_cross = 0;
        float hf_energy = 0.0f;
        for (int i = 0; i < FFT_SAMPLES; i++) {
            float val = i2s_data[i] / 32768.0f;
            fft_buffer[i * 2 + 0] = val;
            fft_buffer[i * 2 + 1] = 0.0f;
            rms += val * val;
            if (i > 0 && ((i2s_data[i] >= 0 && i2s_data[i-1] < 0) || (i2s_data[i] < 0 && i2s_data[i-1] >= 0))) {
                zero_cross++;
            }
            if (i > 0) {
                hf_energy += fabs(val - (i2s_data[i-1] / 32768.0f));
            }
        }
        rms = sqrt(rms / FFT_SAMPLES);
        dsps_fft2r_fc32(fft_buffer, FFT_SAMPLES);
        dsps_bit_rev_fc32(fft_buffer, FFT_SAMPLES);
        dsps_cplx2reC_fc32(fft_buffer, FFT_SAMPLES);
        mfcc_features[0] = rms;
        mfcc_features[1] = (float)zero_cross / FFT_SAMPLES;
        mfcc_features[2] = hf_energy / FFT_SAMPLES;
        float loss_sum = 0.0f;
        for(int j=0; j<ML_FEATURES; j++) {
            float z = (mfcc_features[j] - baseline_mean[j]) / baseline_std[j];
            loss_sum += (z * z * shunt_autoencoder_weights[j]); 
        }
        z_score_loss = sqrt(loss_sum);
        if (deviceConnected) {
            uint8_t packet[64];
            for(int i=0; i<64; i++) packet[i] = (uint8_t)((i2s_data[i*16] >> 8) + 128);
            pCharTelemetry->setValue(packet, 64);
            pCharTelemetry->notify();
            pCharInference->setValue((uint8_t*)&z_score_loss, sizeof(z_score_loss));
            pCharInference->notify();
        }
        vTaskDelay(pdMS_TO_TICKS(16));
    }
}
void setup() {
    Serial.begin(115200);
    Serial.println("Booting ShuntWhisper Edge Device...");
    setupI2S();
    setupBLE();
    xTaskCreatePinnedToCore(
        coreInferenceTask,
        "InferenceEngine",
        10000,
        NULL,
        1,
        &InferenceTask,
        1
    );
}
void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
