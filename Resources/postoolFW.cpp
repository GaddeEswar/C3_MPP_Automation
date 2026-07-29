#include <AccelStepper.h>

// Define the stepper motors and the pins they are connected to
AccelStepper stepperX(AccelStepper::DRIVER, 2, 5); // X-axis (Step, Direction)
AccelStepper stepperY(AccelStepper::DRIVER, 3, 6); // Y-axis
AccelStepper stepperZ(AccelStepper::DRIVER, 4, 7); // Z-axis

void setup() {
  Serial.begin(115200);
  stepperX.setMaxSpeed(1000);
  stepperX.setAcceleration(500);
  stepperY.setMaxSpeed(1000);
  stepperY.setAcceleration(500);
  stepperZ.setMaxSpeed(1000);
  stepperZ.setAcceleration(500);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    executeCommand(command);
  }
}

void executeCommand(String command) {
  // Split the command into parts
  int separatorIndex = command.indexOf(' ');
  String action = command.substring(0, separatorIndex);
  String value = command.substring(separatorIndex + 1);

  // Handle different actions
  if (action == "MOVE_X") {
    if (value == "Home"){
      stepperX.moveTo(0);
      stepperX.runToPosition();   
    }else if(value == "SetHome"){
      stepperX.setCurrentPosition(0);
    }else{
      stepperX.move(value.toInt());
      stepperX.runToPosition();
    }
  } else if (action == "MOVE_Y") {
    if (value == "Home"){
      stepperY.moveTo(0);
      stepperY.runToPosition();   
    }else if(value == "SetHome"){
      stepperY.setCurrentPosition(0);
    }else{
      stepperY.move(value.toInt());
      stepperY.runToPosition();
    }
  } else if (action == "MOVE_Z") {
    if (value == "Home"){
      stepperZ.moveTo(0);
      stepperZ.runToPosition();   
    }else if(value == "SetHome"){
      stepperZ.setCurrentPosition(0);
    }else{
      stepperZ.move(value.toInt());
      stepperZ.runToPosition();
    }
  } 
   else if (action == "Settings"){
    //Redefine the motor speed and accelarations
    int Sindex = value.indexOf(':');
    String Speed = value.substring(0);
    String  Acceleration = value.substring(1);
    // Serial.println(Speed);
    // Serial.println(Acceleration);

  }
}
