float Geschwindigkeit;
float timea=0;
float timeb;
float timec;
int a=0;
int b=0;
void setup() {
  // put your setup code here, to run once:
  pinMode(A0, INPUT);
  Serial.begin(9600);
}
void loop() {
  a = b;
  b = analogRead(A0);
  if (b - a > 800) {
    timea = timeb;
    timeb = millis();
    Geschwindigkeit = round(1000 / (timeb - timea) * 1.326);
    Serial.println(Geschwindigkeit);
  }
  timec = millis();
  if ((timec - timeb) > 1000) Serial.println(0);
  delay(5);
}

