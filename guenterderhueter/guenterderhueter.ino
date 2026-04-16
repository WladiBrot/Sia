int Relais=0;

void setup() {
  // put your setup code here, to run once:
  pinMode(7, OUTPUT);
  Serial.begin(9600);
  digitalWrite(7, LOW);
}

void loop() {
  // put your main code here, to run repeatedly:
  float Spannung = analogRead(A0) *(5.0 / 1023.0);
  Serial.print("Spannung:");
  Serial.println(Spannung);
  if(Spannung>=4.15 && Relais==0){
    digitalWrite(7, HIGH);
    Serial.println("Relais EIN");
    delay(2000);
    Relais=1;
  }
  if(Spannung<4.15 && Relais==1){
    digitalWrite(7, LOW);
    Serial.println("Relais AUS");
    delay(2000);
    Relais=0;
  }
}
