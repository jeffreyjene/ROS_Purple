// =======================
// Pin Definitions (YOUR CONFIG)
// =======================

// Right encoder
#define ENCA_R 2   // interrupt
#define ENCB_R 5

// Left encoder
#define ENCA_L 3   // interrupt
#define ENCB_L 6

// Motor driver TB6612FNG
#define PWMA 9
#define AIN1 13
#define AIN2 12

#define PWMB 11
#define BIN1 7
#define BIN2 8

#define STBY 4

// =======================
// Globals
// =======================

volatile long ticks_left = 0;
volatile long ticks_right = 0;

int pwm_left = 0;
int pwm_right = 0;

unsigned long last_send = 0;
const int SEND_INTERVAL = 50; // ms

// 🔥 Motor calibration (TUNE THIS)
float gain_left = 0.96;
float gain_right = 1.0;  // start here (reduce right side)

// =======================
// Setup
// =======================

void setup() {
  Serial.begin(115200);

  // Encoder pins
  pinMode(ENCA_R, INPUT_PULLUP);
  pinMode(ENCB_R, INPUT_PULLUP);
  pinMode(ENCA_L, INPUT_PULLUP);
  pinMode(ENCB_L, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENCA_R), rightEncoderISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENCA_L), leftEncoderISR, CHANGE);

  // Motor pins
  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH); // enable motor driver

  stopMotors();
}

// =======================
// Main Loop
// =======================

void loop() {
  readSerial();
  driveMotors();

  if (millis() - last_send >= SEND_INTERVAL) {
    sendEncoders();
    last_send = millis();
  }
}

// =======================
// Encoder ISRs
// =======================

void rightEncoderISR() {
  bool a = digitalRead(ENCA_R);
  bool b = digitalRead(ENCB_R);

  if (a == b) ticks_right++;
  else ticks_right--;
}

void leftEncoderISR() {
  bool a = digitalRead(ENCA_L);
  bool b = digitalRead(ENCB_L);

  if (a == b) ticks_left--;
  else ticks_left++;
}

// =======================
// Motor Control
// =======================

void setMotor(int pwmPin, int in1, int in2, int speed) {
  speed = constrain(speed, -255, 255);

  if (speed > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
    analogWrite(pwmPin, speed);
  } 
  else if (speed < 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
    analogWrite(pwmPin, -speed);
  } 
  else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(pwmPin, 0);
  }
}

void driveMotors() {

  // 🔥 Apply gain correction
  int out_left = pwm_left * gain_left;
  int out_right = pwm_right * gain_right;

  out_left = constrain(out_left, -255, 255);
  out_right = constrain(out_right, -255, 255);

  // IMPORTANT: mapping stays the same
  setMotor(PWMA, AIN1, AIN2, out_right); 
  setMotor(PWMB, BIN1, BIN2, out_left);
}

void stopMotors() {
  pwm_left = 0;
  pwm_right = 0;
  driveMotors();
}

// =======================
// Serial Communication
// =======================

void readSerial() {
  static String buffer = "";

  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      processCommand(buffer);
      buffer = "";
    } else {
      buffer += c;
    }
  }
}

void processCommand(String cmd) {
  if (cmd.startsWith("CMD")) {
    int l, r;

    if (sscanf(cmd.c_str(), "CMD %d %d", &l, &r) == 2) {
      pwm_left = constrain(l, -255, 255);
      pwm_right = constrain(r, -255, 255);
    }
  }

  if (cmd.startsWith("STOP")) {
    stopMotors();
  }
}

// =======================
// Encoder Output
// =======================

void sendEncoders() {
  noInterrupts();
  long l = ticks_left;
  long r = ticks_right;
  interrupts();

  Serial.print("ENC ");
  Serial.print(l);
  Serial.print(" ");
  Serial.println(r);
}