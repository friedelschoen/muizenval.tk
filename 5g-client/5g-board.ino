#include "command.h"
#include "config.h"

void setup() {
	// -*- hardware initiation -*-
	pinMode(powerPin, OUTPUT);		// Put voltage on the nb-iot module
	pinMode(voltagePin, OUTPUT);	// Switch module voltage
	pinMode(enablePin, OUTPUT);		// Set state to active

	digitalWrite(powerPin, HIGH);
	digitalWrite(voltagePin, LOW);
	digitalWrite(enablePin, HIGH);

	usbSerial.begin(baud);
	while (usbWait && !usbSerial)
		;

	modemSerial.begin(baud);
	while (!modemSerial)
		;


	// -*- module initialization -*-
	usbSerial.print("[INFO] waiting for module to start up");
	for (;;) {
		usbSerial.print('.');
		modemSerial.write("AT\r\n");
		delay(1000);
		if (modemSerial.available())
			break;
	}
	while (modemSerial.available())	   // clear cache
		modemSerial.read();
	usbSerial.println();

	sendCommand("ATE0");	// disable command-echo

	char info[256];
	sendCommand("ATI", info);

	usbSerial.println("[INFO] module information:");
	usbSerial.println(info);

	//	if (sendCommand("AT+CPIN=\"" SIM_PIN "\"") == COMMAND_ERROR) {
	//		usbSerial.println("[EROR] sim can't be unlocked, wrong PIN");
	//		return;
	//	}
	usbSerial.println("[INFO] sim successful unlocked");

	sendCommand("AT+CPSMS=0");	   // Disable Power Saving Mode
	sendCommand("AT+CEDRXS=0");	   // Disable eDRX
	usbSerial.println("[INFO] disabled power safe");

	// -*- internet initialization -*-
	sendCommand("AT+CFUN=15", COMMAND_BLOCK);							 // Reset the module
	sendCommand("AT+UMNOPROF=1", COMMAND_BLOCK);						 // Set MNO profile (1=automatic,100=standard europe)
	sendCommand("AT+URAT=7,8");											 // Set URAT to LTE-M/NB-IOT
	sendCommand("AT+CEREG=3", COMMAND_BLOCK);							 // Enable URCs
	sendCommand("AT+CGDCONT=1,\"IP\",\"" simAPN "\"", COMMAND_BLOCK);	 // Set the APN
	sendCommand("AT+COPS=0,2");											 // Autoselect the operator

	usbSerial.print("[INFO] waiting for connection");

	char response[100];

	// Check Siganl strenght, repeat till you have a valid CSQ (99,99 means no signal)
	while (sendCommand("AT+CSQ", response, COMMAND_SILENT) == COMMAND_OK && !strcmp(response, "+CSQ: 99,99")) {
		delay(1000);
		usbSerial.print(".");
	}

	// Wait for attach, 1 = attached
	while (sendCommand("AT+CGATT?", response, COMMAND_SILENT) == COMMAND_OK && strcmp(response, "+CGATT: 1")) {
		delay(1000);
		usbSerial.print(".");
	}
	usbSerial.println();

	usbSerial.println("[INFO] connected!");

	// -*- server connection -*-

	/*
AT+UHTTP=0,0,"86.92.67.21"

AT+UHTTP=0,5,80

AT+UHTTPC=0,5,"/api/search_connect","","TEST!",1

	*/

	sendCommand("AT+UHTTP=0,0,\"86.92.67.21\"");
	sendCommand("AT+UHTTP=0,5,80");
	sendCommand("AT+UHTTPC=0,5,\"/api/search_connect\",\"\",\"TEST!\",1");


	usbSerial.println("[INFO] initiation completed, starting passthrough:");
}

void loop() {
	// -*- passthrough for custom commands -*-
	while (usbSerial.available())
		modemSerial.write(usbSerial.read());

	while (modemSerial.available())
		usbSerial.write(modemSerial.read());
}