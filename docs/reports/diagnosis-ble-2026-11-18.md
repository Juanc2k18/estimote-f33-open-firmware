# First BLE test and disconnection after ten seconds

Date: 2026. Test performed by the owner, not by the agent. [Original log](../evidence/ble_scanner_20261118_135334.txt).

## Observations

The owner reports that the 5 V and GND contacts match the reference provided, that they connected them and were able to connect the phone to the beacon. No internal VDD measurements or oriented photo of the wiring were provided; these contacts are not yet assigned to E1/E2/E3/E4. The external 5 V input is not identified with the MCU's VDD.

The capture shows CONNECTED and NOT BONDED: a GATT connection, with no persistent BLE bond indicated. In each session the log discovers four services and nine characteristics, successfully negotiates MTU 23 and records four disconnections with GATT status GATT_SUCCESS (0).

| Connected | Disconnected | Duration |
| --- | --- | --- |
| 13:53:35.303 | 13:53:45.184 | 9.881 s |
| 13:54:08.660 | 13:54:18.475 | 9.815 s |
| 13:54:26.376 | 13:54:36.351 | 9.975 s |
| 13:55:02.312 | 13:55:12.201 | 9.889 s |

The log contains no attempts to read values, write characteristics or enable notifications. Nor does it contain the HCI disconnection reason; status 0 in the Android callback does not by itself identify who closed the link or why.

## Discovered services

Proprietary base UUID: `xxxxxxxx-d2cc-11e4-9a1f-0002a5d5c51b`.

| Service | Observed characteristics and properties |
| --- | --- |
| Generic Access 0x1800 | 0x2A00, 0x2A01 and 0x2A04: Read |
| Generic Attribute 0x1801 | 0x2A05: Indicate |
| 6c372000… | 6c372001…: Write No Response; 6c372002…: Write and Notify; 6c372004…: Read |
| 6c371000… | 6c371002…: Notify; 6c371001…: Write and Write No Response |

No semantic function is attributed to the proprietary characteristics based only on their properties or UUID. Their presence does not show that UART is enabled.

## Interpretation and source

[Estimote's official documentation on connections](https://d3lgd0yxjqbzck.cloudfront.net/managing-beacons/connecting-to-beacons/) explains that a generic scanner can connect, but the beacon expects authorization and disconnects after roughly ten seconds when it is not completed. The SDK obtains the beacon's credentials through the cloud account. The recorded behavior is very consistent with that mechanism; it is still an inference, with no HCI capture or internal firmware log. Current cloud access or authentication with the SDK has not been tested on this unit.

It is not a BLE rule that an application with no requests must disconnect after ten seconds. [Nordic explains](https://academy.nordicsemi.com/courses/bluetooth-low-energy-fundamentals/lessons/lesson-3-bluetooth-le-connections/topic/connection-process/) that even without useful data, empty packets are exchanged to keep synchronization. Link supervision is distinct from the Estimote application's authorization deadline.

## Next check

Within a connection, read the standard characteristics 0x2A00 (name), 0x2A01 (appearance) and 0x2A04 (preferred parameters), and save the results or errors. If the proprietary characteristic 6c372004… is to be explored, use only Read and record the bytes without attributing meaning to them in advance. These readings do not replace authorization and are not expected to remove its deadline. For the next stage it is also worth saving the raw BLE advertisements; this file only records connections and GATT discovery.

Status: working external power and GATT connection reported by the owner; authorized configuration, UART and SWD pending.

## Readings provided later, 13:59 capture

The later capture shows these values retained in the interface, already in DISCONNECTED / NOT BONDED state:

- 0x2A00 Device Name: `estimote`, hexadecimal `657374696D6F7465`.
- 0x2A01 Appearance: the app shows `UNKNOWN`; it does not display bytes, so it cannot be stated that the value is 0x0000, nor can an unknown value be told apart from a reading with no result.
- 0x2A04 Peripheral Preferred Connection Parameters: `8000A0000000F401`. Interpreted as four little-endian 16-bit integers: 128, 160, 0, 500. Preferred minimum interval 160 ms; maximum 200 ms; peripheral latency 0 events; preferred supervision timeout 5 s.

[Nordic reference on units and negotiation](https://academy.nordicsemi.com/courses/designing-low-power-bluetooth-le-products/lessons/lesson-4-bluetooth-le-power-optimization/topic/exercise-2-optimizing-power-consumption-in-a-bluetooth-le-connection/?version=v3.4.1). These are the peripheral's preferences: they do not prove the effective parameters Android negotiated. The supervision timeout is not a timer that disconnects for lack of GATT reads. The new values do not replace the explanation of the Estimote authorization deadline, nor do they prove configuration access.

The capture also shows 0x2A05 Service Changed with the Indicate property, with no values to analyze. Suggested next reading: proprietary characteristic 6c372004-d2cc-11e4-9a1f-0002a5d5c51b (Read), saving the bytes or the exact error, without writing to the other characteristics.
