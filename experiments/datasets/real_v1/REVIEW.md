# Review sheet: real_v1

54 questions. For each one, check: is the question clear and realistic? Do the passages below really answer it, and is any relevant passage missing (search the corpus for it)? Are the key facts correct and short? Is the expected behaviour right? Write changes into dataset.yaml and note them in `notes`. Reviewer initials: ______

## r01 (lookup) [ ] checked

**Q:** In the Q-factor measurement method, how is the coil circuit made to ring on its own?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** qfactor · abstract → 2 passage(s)

> *US10804750B2.txt, abstract:* A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor from monitoring the voltage.  RELATED DOCUMENTS  [0001] This application claims priority to U.S. Provisional Patent Application 62/546,988, filed on Aug. 17, 2017, which is herein incorporated by reference in its entirety.

> *US10804750B2.txt, summary:* [0006] In accordance with some embodiments of the present invention, a wireless power transmitter that measures the Q-factor is provided. In accordance with some embodiments, the wireless power transmitter includes a transmit coil; a capacitor coupled in series with the transmit coil to form a resonant circuit; a bridge circuit coupled to the resonant circuit; a control circuit coupled to control the bridge circuit to provide voltages across the resonant circuit; a charging circuit coupled to charge the capacitor with a charging voltage and coupled to be controlled by the control circuit; and a detection circuit coupled to receive a voltage across the capacitor and provide data related to the voltage to the control circuit while the resonant circuit.  [0007] A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor  …


**Key facts:** ground ✓

---

## r02 (lookup) [ ] checked

**Q:** Over what frequency range might a wireless charger sweep when it measures the Q-factor?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** qfactor · "from a low frequency (for example 80 kHz)" → 1 passage(s)

> *US10804750B2.txt, description:* The half-bridge driver formed by transistors Q1 204 and Q3 208 can then drive the LC resonant circuit formed by transmit coil Lp 106 and capacitor Cp 114.  [0029] As is further illustrated in FIG. 2A, the voltage at a node between transmit coil 106 and capacitor 114 is input to a diode D1 212. The output signal from diode D1 212 is then input to Envelop Detection Circuit 214. Diode D1 212 can operate as a rectifier while envelop detection circuit 214 can produce the RMS voltage V1 across capacitor Cp 114. Tracking the amplitude of the resonant capacitor voltage, V1, can be used to determine the Q-factor of the LC resonant circuit.  [0030] During the Q-factor detection process, transmitter control circuit 202 sweeps the switching frequency f through a frequency range. The range can be, for example, from a low frequency (for example 80 kHz) to a high frequency (for example 120 kHz) in a frequency step (for example 100 Hz steps). The Transmitter may sweep the frequencies from low-to-high or from high-to-low.  [0031] FIG. 2B illustrates the voltage as a function of frequency during the sweep. As is illustrated in FIG. 2B, by sweeping through the frequency range, transmitter control cir …


**Key facts:** 80 kHz ✓; 120 kHz ✓

---

## r03 (lookup) [ ] checked

**Q:** By default, how long does each foreign object detection window last in the charger that uses a separate sensing coil?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sensing_coil · "periods TP of about 100 microseconds" → 1 passage(s)

> *US11316383B1.txt, description:* [0047] To help enhance measurement accuracy by device 12 during foreign object detection periods TP, device 12 can evaluate the quality of the foreign object detection measurements being made by device 12. Device 12 can then adjust the timing of periods TP (e.g., start and end times for each period TP) so that these periods tend to coincide with low-noise time periods such as periods TP′.  [0048] A flow chart of illustrative operations involved in using system 8 in a configuration in which device 12 evaluates the quality of foreign object detection measurements so that the timing of foreign object detection measurements can be adjusted to enhance measurement quality is shown in FIG. 11.  [0049] During the operations of block 11, the control circuitry of device 12 operates device 12 with default settings. For example, device 12 may initially be configured so that periods TP of about 100 microseconds (e.g., at least 10 microseconds, at least 50 microseconds, less than 1000 microseconds, less than 500 microseconds, etc.) alternate with periods TN of at least 10 ms, at least 100 ms, at least 1 s, at least 10 s, less than 20 s, less than 2 s, less than 200 ms, less than 20 ms, or less t …


**Key facts:** 100 microseconds ✓

---

## r04 (lookup) [ ] checked

**Q:** What does the charger do when the measured Q factor drifts too far from its baseline value?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sensing_coil · "deviates by more than a threshold amount from the baseline" → 1 passage(s)

> *US11316383B1.txt, description:* [0050] During the operations of block 122, device 12 makes foreign object detection measurements (e.g., Q-factor measurements and comparisons) in periods TP. Device 12 also determines the quality of these measurements. For example, because the expected signal during periods TP follows the function e−αt(sin(2πft)), this function can be used as a basis function in a least-squares curve fitting process. If the fit between the basis function and the measured signal on coil 36 during period TP is poor, signal quality metric QM will be relatively low, indicating that the quality of the signal on coil 36 is low because noise is present. If, however, the fit between the basis function and the measured signal on coil 36 during period TP is good, quality metric QM will be relatively high, indicating that the quality of the signal on coil 36 is high due to the absence of interference. Quality metric QM may be determined in this way whether or not sensing coil 86 is present and is being used to measure noise for subtraction from the signal on coil 36.  [0051] If the measured Q factor from step 122 deviates by more than a threshold amount from the baseline Q factor, a foreign object is likely p …


**Key facts:** halted ✓

---

## r05 (lookup) [ ] checked

**Q:** How does the machine-learning based charging pad decide whether a foreign object is present?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** ml_fod · abstract → 1 passage(s)

> *US20190074730A1.txt, abstract:* A wireless power transmission system has a wireless power receiving device with a wireless power receiving coil that is located on a charging surface of a wireless power transmitting device with a wireless power transmitting coil array. Control circuitry in the wireless power transmitting device may use inverter circuitry to supply alternating-current signals to coils in the coil array, thereby transmitting wireless power signals. The control circuitry may also be used to detect foreign objects on the coil array such as metallic objects without wireless power receiving coils. For example, control circuitry may use inductance measurements from the coils in the coil array to determine a probability value indicative of whether a foreign object is present on the charging surface. The control circuitry may compare the probability value to a threshold and take suitable action in response to the comparison.  [0001] This application claims the benefit of provisional patent application No. 62/554,426, filed on Sep. 5, 2017, which is hereby incorporated by reference herein in its entirety.


**Label:** ml_fod · "probability value indicative of whether a foreign object is present" → 8 passage(s)

> *US20190074730A1.txt, abstract:* A wireless power transmission system has a wireless power receiving device with a wireless power receiving coil that is located on a charging surface of a wireless power transmitting device with a wireless power transmitting coil array. Control circuitry in the wireless power transmitting device may use inverter circuitry to supply alternating-current signals to coils in the coil array, thereby transmitting wireless power signals. The control circuitry may also be used to detect foreign objects on the coil array such as metallic objects without wireless power receiving coils. For example, control circuitry may use inductance measurements from the coils in the coil array to determine a probability value indicative of whether a foreign object is present on the charging surface. The control circuitry may compare the probability value to a threshold and take suitable action in response to the comparison.  [0001] This application claims the benefit of provisional patent application No. 62/554,426, filed on Sep. 5, 2017, which is hereby incorporated by reference herein in its entirety.

> *US20190074730A1.txt, summary:* [0004] A wireless power transmission system has a wireless power receiving device that is located on a charging surface of a wireless power transmitting device. The wireless power receiving device has a wireless power receiving coil and the wireless power transmitting device has a wireless power transmitting coil array. Control circuitry may use inverter circuitry in the wireless power transmitting device to supply alternating-current signals to coils in the coil array, thereby transmitting wireless power signals.  [0005] Signal measurement circuitry coupled to the coil array may make measurements while the control circuitry uses the inverter circuitry to apply excitation signals to each of the coils. The control circuitry can analyze measurements made with the signal measurement circuitry to determine the values of inductances and other measurements associated with the coils in the coil array.  [0006] Foreign objects on the coil array such as metallic objects without wireless power receiving coils can be detected using machine-learning-based foreign object detection. For example, control circuitry may use inductance measurements and other measurements from the coils in the coil ar …


**Key facts:** probability ✓; threshold ✓

---

## r06 (lookup) [ ] checked

**Q:** At roughly what frequency does the machine-learning charging pad transmit power?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** ml_fod · "a predetermined frequency of about 125 kHz" → 1 passage(s)

> *US20190074730A1.txt, description:* Power is conveyed wirelessly from device 12 to device 24 during these FSK and ASK transmissions.  [0025] During wireless power transmission operations, circuitry 52 supplies AC drive signals to one or more coils 42 at a given power transmission frequency. The power transmission frequency may be, for example, a predetermined frequency of about 125 kHz, at least 80 kHz, at least 100 kHz, less than 500 kHz, less than 300 kHz, or other suitable wireless power frequency. In some configurations, the power transmission frequency may be negotiated in communications between devices 12 and 24. In other configurations, the power transmission frequency is fixed.  [0026] During wireless power transfer operations, while power transmitting circuitry 52 is driving AC signals into one or more of coils 42 to produce signals 44 at the power transmission frequency, wireless transceiver circuitry 40 uses FSK modulation to modulate the power transmission frequency of the driving AC signals and thereby modulate the frequency of signals 44. In device 24, coil 48 is used to receive signals 44. Power receiving circuitry 54 uses the received signals on coil 48 and rectifier 50 to produce DC power. At the sam …


**Key facts:** 125 kHz ✓

---

## r07 (lookup) [ ] checked

**Q:** Which everyday metal objects are given as examples of foreign objects that heat up from eddy currents in the detection-coil patent?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** fod_coils · "(e.g. a ring or a coin)" → 2 passage(s)

> *US9178361B2.txt, description:* It can be seen that the power transfer of P2 is mainly due to interaction between the electromagnetic field with the friendly parasitic components 424. There are two reasons that the energy represented by arrow P2 leaks from the system, thereby decreasing the efficiency of the wireless power transfer system 400.  [0048] First, the transmitter coil 408 and receiver coil 412, and their corresponding shielding 404 and 416, are usually not matched in dimensions. In many embodiments, the transmitter coil 408 is designed to be larger than the receiver coil 412 and the receiver shielding 416, such that the receiver coil has a wider range of acceptable charging locations with respect to the transmitter coil 408. Second, the receiver shielding 416, as shown in FIG. 4( a), typically does not completely isolate the friendly parasitic component 424 from the field P2 for practical reasons, such as cost.  [0049] The third part of the field, represented by the arrow P3, and the corresponding induced power goes into the foreign object 420. When the foreign object 420 is metal (e.g. a ring or a coin) and positioned within this field, an eddy current will be induced inside the metal object. Electrom …

> *US9178361B2.txt, description:* When the foreign object 420 is metal (e.g. a ring or a coin) and positioned within this field, an eddy current will be induced inside the metal object. Electromagnetic energy will be converted into electrical power loss. The metal foreign object 420 will dissipate this electrical power by becoming hot.  [0050] One way of applying the previously described oscillation and decay method to detect foreign objects in a wireless power transfer system is to use the transmitter coil 408 shown in FIGS. 4( a) and 4(b) as a foreign object detection coil. However, when the energy oscillates between the transmitter coil 408 and the added capacitor (shown in FIGS. 2( a) and 2(b) as capacitor 208), the field generated by the transmitter coil not only induces power loss in the targeted foreign object 420, but also in, for example, the friendly parasitic components 424. In other words, referring again to FIG. 2( b), the ‘R+jX’ component will include all these factors, which cannot be easily separated.  [0000] Using Detector Coils for Foreign Object Detection  [0051] In many cases, the foreign object can be assumed to be smaller than the friendly parasitic components 424 and/or the power transmitter  …


**Key facts:** ring ✓; coin ✓

*Notes:* Several patents mention coins; the ring example is specific to fod_coils.

---

## r08 (lookup) [ ] checked

**Q:** Why are the foreign object detection coils made smaller than the power transmitter coil?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** fod_coils · abstract → 1 passage(s)

> *US9178361B2.txt, abstract:* Methods and systems are described for using detection coils to detect metallic or conductive foreign objects that can interfere with the wireless transfer of power from a power transmitter to a power receiver. In particular, the detection coils are targeted to foreign objects that are smaller than a power transmitter coil in the power transmitter.


**Key facts:** smaller ✓

---

## r09 (lookup) [ ] checked

**Q:** How does the inductive charging system with a detection coil layer confirm that an object is near the charging area?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** impedance_fod · "between input impedance 605 and input impedance 609" → 1 passage(s)

> *US20220115917A1.txt, description:* [0052] A comparison system declares a presence of a foreign object in proximity to the charging area of a wireless power transfer system in response to a difference 608 between input impedance 605 and input impedance 609 exceeding a threshold value.  [0053] Even though there is a change on input impedance of the detection coil due to the existence of the metal object, the variation itself is relatively small and measurement may be difficult without amplification. In some embodiments, a resonant circuit 700 may be applied to the detection coil to amplify the impedance variation. An equivalent circuit of an exemplary embodiment of the resonant circuit 700 is shown in FIG. 7. A series connected capacitor 701 and a parallel connected capacitor 702 resonate together with a detection coil 704. A voltage source 705 and a resistor 709 may be provided in series, and the series connected voltage source 705 and resistor 709 may be connected in parallel with the parallel connected capacitor 702. The right side of FIG. 7 is similar to FIG. 6C; therefore, like reference numerals and descriptions of like structures are omitted herein for brevity.  [0054] As shown in FIG. 8, in an exemplary embodi …


**Label:** impedance_fod · "detect a change in impedances of the detection coils" → 1 passage(s)

> *US20220115917A1.txt, summary:* The detection coil layer may be a four-layer coil pattern. Individual detection coils of the detection coil layer may overlap to eliminate a gap between each detection coil. A cover may be disposed on the detection coil layer.  [0010] In an exemplary embodiment, a processor may be configured to detect a change in impedances of the detection coils to detect the object disposed on the detection coil layer. The processor may be configured to convert the change in impedances to an output voltage signal through a resonant circuit and a signal processing circuit. To confirm presence of the object, the processor may be configured to determine a difference between an impedance when no object is disposed on the detection coil layer and an impedance when the object is disposed on the detection coil layer to be greater than a predetermined threshold.  [0011] In an exemplary embodiment, the inductive wireless power transfer system may include a resonant circuit. The resonant circuit may include a first capacitor connected in series to a detection coil of the detection coil layer and a second capacitor connected in parallel to the detection coil.  [0012] In an exemplary embodiment, the inductiv …


**Key facts:** impedance ✓; threshold ✓

---

## r10 (lookup) [ ] checked

**Q:** How much driving range can an electric vehicle lose because of poor battery thermal management?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** predictive · "reduced by up to 10-15%" → 2 passage(s)

> *US20190315232A1.txt, background:* [0002] In recent years, vehicle powering methods have changed substantially. This change is due in part to a concern over energy efficiency, utilization of renewable resources, and a societal shift to adopt more environmentally friendly power solutions. These considerations have encouraged the development of a number of new battery systems for electric vehicles.  [0003] While conventional battery systems appear to be new they are generally implemented as a number of traditional subsystems that are merely tied to an alternative power system. In fact, the design and construction of battery systems is typically limited to standard vehicle concepts. Among other things, these limitations fail to take advantage of the benefits of new technology, vehicle information systems, and processing power.  [0004] Batteries in battery electric vehicles (“BEVs”) can store electricity allowing users of electric vehicles to travel distances. The range of a BEV is in some ways limited to the battery size as well as amount of battery energy consumption. Currently, batteries in BEVs are large, heavy and expensive. The use of large and heavy batteries in a BEV results in a BEV of an increased size. A BEV  …

> *US20190315232A1.txt, background:* In some cases, the range of a BEV can be reduced by up to 10-15% due to poor thermal management of the battery. As such, the thermal management of a BEV battery should be minimized to maximize vehicle range.  [0006] As battery size and/or capacity of BEVs increase, the power requirement per-battery cell decreases. This reduces the amount of heat generated by the battery; thus, most driving conditions do not require cooling. However, for certain use cases such as high-speed driving, continual uphill driving, DC-fast charging, and hot climates, a battery may reach a threshold temperature and active cooling may be required.  [0007] Current battery thermal control schemes are reactive—sensor data and set limits are used to control cooling power to battery thermal management system. Typical conventional systems often focus on the overall control of the battery thermal management system based on known information about a vehicle, that is information gathered during the design phase of the vehicle, in which the system is characterized under a number of different situations. This results in a heuristic based approach which may lower energy usage in some situations; such an approach, howeve …


**Key facts:** 10-15% ✓

---

## r11 (lookup) [ ] checked

**Q:** Which estimation technique is used to compute the average temperature of a battery system from sensor and ambient readings?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** kalman · abstract → 1 passage(s)

> *US20160079633A1.txt, abstract:* System and methods for estimating a temperature of a battery are presented. In some embodiments, a method of estimating a temperature of a battery system may utilize measured battery system temperature data and measured ambient temperature data. Based on the measured temperature data, an average estimated temperature of the battery system may be determined using, at least in part, an extended Kalman filter and an energy balance process model associated with the battery system.


**Label:** kalman · claim 1 → 1 passage(s)

> *US20160079633A1.txt, claim 1:* 1. A method of estimating a temperature of a battery system, the method comprising: receiving battery system temperature measurement data from one or more first temperature sensors associated with the battery system; receiving ambient temperature measurement data associated with an ambient temperature proximate to the battery system from one or more second sensors associated with the battery system; and determining an average estimated temperature of the battery system using, at least in part, an extended Kalman filter based on the battery system temperature measurement data, the ambient temperature measurement data, an energy balance process model associated with the battery system, and a temperature parameter.


**Key facts:** extended Kalman filter ✓

---

## r12 (lookup) [ ] checked

**Q:** What coolant mixture is suggested for the coolant loop of the combined HVAC and battery thermal system?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** hvac_chiller · "ethylene glycol and water mix" → 1 passage(s)

> *US20090249807A1.txt, description:* Refrigerant exiting the chiller 48 is directed through a return portion of the battery thermal expansion valve 46 and back to the compressor 28 to complete the second leg 36 of the refrigerant loop 26.  [0014] The chiller 48 is also in fluid communication with a coolant loop 50. The dashed lines in FIGS. 1 and 3 represent conduits through which refrigerant flows, while the dash-dot lines represent conduits through which a coolant liquid flows. The coolant may be a conventional liquid mixture such as an ethylene glycol and water mix, or may be some other type of liquid with suitable heat transfer characteristics.  [0015] The coolant loop 50 may also include a coolant pump 52 for pumping the coolant through the loop 50. The coolant loop 50 flows through a battery pack 54, where the coolant is employed to cool the battery pack 54. A coolant routing valve 58 is located in the coolant loop 50 and can be selectively actuated to redirect the coolant through three different branches of the coolant loop 50. A first outlet 62 of the valve 58 directs coolant to a first branch 60, which includes a battery radiator 64. The battery radiator 64 may be positioned to have air flowing through it to  …


**Key facts:** ethylene glycol ✓

---

## r13 (lookup) [ ] checked

**Q:** How can a rapid charging station identify which vehicle has just arrived?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** offboard · "scanning an RFID tag or VIN number" → 1 passage(s)

> *US20170297431A1.txt, description:* The off-board system may use this chemistry to determine what current and voltage to feed the on-board batteries.  [0020] According to embodiments of the present invention, this information may be compiled in a database which the recharging station may access before initiating the rapid recharge.  [0021] Embodiments of the present invention may also include a control system with the ability to monitor the coolant temperature and cell temperature at various points within the battery pack to ensure safety during this rapid recharging process. The off-board system may contain controls to regulate the flow rate and coolant temperature. The sensors on-board the vehicle may relay information back to the off-board system to regulate the flow rate and temperature.  [0022] Additionally, there is the potential for a waste heat recovery system associated with the off-board thermal management system. Since a significant amount of heat is lost during charging, this waste energy could be extracted via the higher temperature coolant exiting the vehicle after charging.  [0023] The off-board rapid recharging system may first identify the type of vehicle which has just pulled into the recharging sta …


**Key facts:** RFID ✓; VIN ✓

---

## r14 (lookup) [ ] checked

**Q:** Which type of control is used to compute the electronic expansion valve position from chiller outlet measurements?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** pid_chiller · abstract → 1 passage(s)

> *US20230415612A1.txt, abstract:* The present disclosure provides a method of managing thermal loads in an electric vehicle and controlling various electronic components of a thermal management system. The method may comprise heating a battery coolant of a battery coolant loop utilizing waste heat from a battery to form a heated battery coolant, heating a refrigerant of a battery refrigeration loop by exchanging heat with the heated battery coolant, and measuring refrigerant temperature(s) and pressure(s) at an output of a chiller. The measured temperature(s) and pressure(s) may be utilized by the thermal management system as feedback signals for performing a proportional-integral-derivative control to compute an electronic expansion valve position command. Battery temperature(s) and/or battery coolant temperature(s) may be measured and utilized by the thermal management system as feedback signals for computing a pump speed command and performing a proportional-integral-derivative control to compute a compressor speed command and a condenser fan speed command.  CROSS-REFERENCE TO RELATED APPLICATIONS  [0001] This application claims priority to, and the benefit of, U.S. Provisional Patent Application Ser. No. 63/494 …


**Key facts:** proportional-integral-derivative ✓

---

## r15 (lookup) [ ] checked

**Q:** How are the battery cooling loop and the motor cooling loop arranged with respect to the radiator?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** parallel_loops · abstract → 2 passage(s)

> *US11214114B2.txt, abstract:* A traction battery thermal management system is provided. The thermal management system includes a battery loop for regulating the traction battery temperature. A motor loop is provided for regulating a motor temperature. The thermal management system also includes a radiator. A radiator valve selectively controls fluid flow through the radiator. A battery valve selectively couples the battery loop and the motor loops. The battery loop, the motor loop are in fluid communication and arranged in parallel to be cooled by the radiator.  CROSS-REFERENCE TO RELATED APPLICATION  [0001] This application is a continuation of U.S. application Ser. No. 13/757,291 filed Feb. 1, 2013, issued as U.S. Pat. No. 10,046,617 on Aug. 14, 2018, the disclosure of which is incorporated in its entirety by reference herein.

> *US11214114B2.txt, summary:* [0005] In one embodiment, an electric vehicle thermal management system is provided. The thermal management system includes a battery loop for regulating temperature of a traction battery. The battery loop includes a chiller adapted to cool fluid in the battery loop and a battery pump for circulating fluid in the battery loop. A motor loop is provided for regulating temperature of a traction motor and is in fluid communication with the battery loop. The motor loop includes a motor pump for circulating fluid in the motor loop. The motor pump and the battery pump are arranged in parallel. A radiator is n fluid communication with the battery loop and motor loop. A radiator valve selectively controls fluid flow through the radiator. When the radiator valve is in a first position, fluid flows through the radiator. When the radiator valve is in a second position, fluid bypasses the radiator. A battery valve selectively couples the battery loop and the motor loop. When the battery valve is in a first position, fluid flows in parallel through the battery loop and the motor loop. The traction battery is cooled by the radiator without the chiller when both the radiator valve and the battery  …


**Label:** parallel_loops · claim 1 → 1 passage(s)

> *US11214114B2.txt, claim 1:* 1. A thermal management system for a vehicle comprising: a traction battery for propelling the vehicle; a motor coupled to the traction battery; a first cooling loop circulating fluid to cool the traction battery; and a second cooling loop circulating fluid to cool the traction motor; a third loop for regulating a passenger cabin temperature and selectively coupled to the first and second cooling loops; and a radiator selectively in communication with the first cooling loop and second cooling loop, wherein the first loop, the second loop are in fluid communication and arranged in parallel to be cooled by the radiator, a radiator valve for selectively controlling fluid flow through the radiator, wherein in a first position fluid flows through the radiator and in a second position fluid bypasses the radiator, a battery valve for selectively controlling fluid flow through the traction battery, wherein when the radiator valve is in a first position, fluid flows through the radiator and when the battery valve is in a first position fluid flows in parallel through the first loop and the second loop, the radiator thereby cooling the battery and the traction motor in parallel.


**Key facts:** parallel ✓

---

## r16 (lookup) [ ] checked

**Q:** In the compartmentalized immersion-cooled pack, why can't vent gases from one battery module reach another module?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** runners · "fluidly isolated from the other battery modules" → 1 passage(s)

> *US20250079567A1.txt, description:* In an embodiment, the enclosure assembly 28 provides a sealed enclosure around the battery modules 22 and other battery internal components of the traction battery pack 18. The enclosure assembly 28 therefore provides outermost surfaces of the traction battery pack 18.  [0043] Each battery module 22 is compartmentalized and therefore fluidly isolated from the other battery modules 22 of the traction battery pack 18. Accordingly, gases, effluent particles, and/or other vent byproducts vented by one of the battery cells 24 of one of the battery modules 22 cannot flow directly to another of the battery modules 22.  [0044] Each battery module 22 may be spaced apart from the other battery modules 22 of the traction battery pack 18. For example, the battery modules 22 may be separated from one another by their respective housings and an insulation shield 30 disposed between the housings. Additional insulation shields 30 may be positioned between outboard-most battery modules 22 and end walls 26 of the enclosure assembly 28. The insulation shields 30 may be configured to block the transfer of thermal energy from one battery module 22 to another. The insulation shields 30 may further provi …


**Key facts:** isolated ✓

---

## r17 (lookup) [ ] checked

**Q:** What does the control module use to set the position of the flow control valve in an intake runner?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** runners · abstract → 1 passage(s)

> *US20250079567A1.txt, abstract:* Immersion cooling systems are provided for traction battery packs. An exemplary immersion cooling system may include an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and a first interior volume of a compartmentalized battery module, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume. A cooling fluid (e.g., a dielectric) may be selectively communicated through the first interior volume for thermally managing the battery module. A flow control valve may be positioned within the first intake runner for controlling the flow through the first interior volume, and a control module may control a position of the valve based at least on a temperature of the cooling fluid exiting the first interior volume.


**Key facts:** temperature ✓

---

## r18 (lookup) [ ] checked

**Q:** How are vent gases removed in the immersion cooling system that arranges cells in groups separated by dividers?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** grouped · abstract → 3 passage(s)

> *US20230369708A1.txt, abstract:* An immersion cooling system for a battery system includes a battery enclosure and G battery cell groups arranged in the battery enclosure. Each of the G battery cell groups include C battery cells, where G and C are integers greater than one. A plurality of dividers are arranged between each of the G battery cell groups. A gas manifold removes vent gases from each of the G battery cell groups.  INTRODUCTION  [0001] The information provided in this section is for the purpose of generally presenting the context of the disclosure. Work of the presently named inventors, to the extent it is described in this section, as well as aspects of the description that may not otherwise qualify as prior art at the time of filing, are neither expressly nor impliedly admitted as prior art against the present disclosure.  [0002] The present disclosure relates to battery systems, and more particularly to immersion cooling systems for battery systems of electric vehicles.  [0003] Electric vehicles (EVs) such as battery electric vehicles (BEV), fuel cell vehicles or hybrid vehicles include a battery system with one or more battery cells, modules and/or packs. A power control system controls charging an …

> *US20230369708A1.txt, abstract:* During driving, one or more electric motors of the EV receive power from the battery system to provide propulsion for the vehicle and/or to return power to the battery system during regeneration and/or charging from a utility.  [0004] During operation, power is delivered by the battery system to the motor(s) and returned by the motor(s) to the battery system using one or more components such as power inverters, DC-DC converters and/or other components. The battery system is designed to deliver high power when requested, absorb high power quickly during charging from the utility and/or to absorb high power during regeneration.  [0005] The battery systems are expected to continue to increase in power density and operate at higher voltage levels. When operating under these conditions, significant heating of the battery cells, the battery modules, the battery pack, the power inverters, the DC-DC converters and/or other EV components can occur.


**Label:** grouped · claim 1 → 1 passage(s)

> *US20230369708A1.txt, claim 1:* 1. An immersion cooling system for a battery system, comprising: a battery enclosure; G battery cell groups arranged in the battery enclosure, wherein each of the G battery cell groups include C battery cells, where G and C are integers greater than one; a plurality of dividers arranged between each of the G battery cell groups; and a gas manifold configured to receive vent gases from each of the G battery cell groups.


**Key facts:** gas manifold ✓

---

## r19 (lookup) [ ] checked

**Q:** Which charging capability does the improved immersion cooling of grouped battery cells make possible?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** grouped · "enables DC fast charging" → 1 passage(s)

> *US20230369708A1.txt, description:* As a battery cell begins to fail, hot gas/particles are emitted by the battery cell. The hot gas/particles from the failed battery cell can cause heat transfer to other adjacent battery cells. As the adjacent battery cells are heated, they too can fail and cause further failures or propagation.  [0029] An immersion cooling system according to the present disclosure prevents hot gas from heating neighboring battery cells by separating the battery cells into battery cell groups, supplying dielectric fluid to the battery cell groups, and managing vent gas generated by each of the battery cell groups to prevent the vent gas from that battery cell group from causing further battery cell failures due to overheating. In other words, the immersion cooling system prevents hot gas convection to neighboring battery cells to prevent thermal runaway propagation. As will be described further below, the immersion cooling system utilizes edge cooling or both edge and face cooling to prevent thermal runaway propagation to neighboring battery cells.  [0030] The immersion cooling system according to the present disclosure has improved cooling performance that enables DC fast charging while protecting …


**Key facts:** DC fast charging ✓

---

## r20 (lookup) [ ] checked

**Q:** What should the boiling point of the dielectric coolant be in the sealed liquid-cooled battery modules?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sealed · "boiling point at or near a desired operating temperature" → 1 passage(s)

> *US8852772B2.txt, description:* In another embodiment, the gap 24 may be less than 0.25 mm. It is understood that other gap sizes can be used as desired.  [p-0016] A dielectric coolant 28 is disposed within the interior space 16 of the container 14 and the fluid level shown is such that the battery assembly 18 is completely immersed within the dielectric coolant 28. The dielectric coolant 28 is in contact with the battery cells 20 through the fluid channels 26 formed by gaps 24. In one embodiment, the dielectric coolant 28 may be halogenated. In another embodiment, the dielectric coolant 28 may be conditioned to have a boiling point at or near a desired operating temperature of the battery cells 20.  [p-0017] A heating element 34 is located at a base area 36 of the container 14. The heating element 34 shown is an electronic heating element. It is understood that other heating element types may be used. The heating element 34 is shown as a single element; however, multiple heating elements 34 such as heating plates may be provided.  [p-0018] A cooling element 38 is located at an upper area 40 of the container 14. The cooling element 38 may be a chilled water condenser having an inlet 42 and an outlet 44 extending  …


**Key facts:** operating temperature ✓

---

## r21 (lookup) [ ] checked

**Q:** How does the chip cooling module turn the surrounding immersion fluid into jets aimed at the processor?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** electronics · abstract → 1 passage(s)

> *US12563707B2.txt, abstract:* Embodiments of the present invention provide a cooling module for cooling heat-generating electronic devices in an immersion cooling system. The cooling module includes an integrated pump, which draws immersion fluid from the surrounding dielectric bath and drives it into a pressurized plenum to pressurize the coolant fluid and drive the pressurized coolant fluid through a nozzle plate containing a microconvective nozzle array. The array accelerates the fluid to produce a multiplicity of microjets that impinge on a surface of the heat-generating electronic device to be cooled. The effluent from the cooling module may be directed to flow into and wash over nearby heat-generating devices to help cool the nearby heat-generating devices. The effluent may also be directed to the inlets of daughter cooling modules attached to other heat-generating electronic devices. In some embodiments, cooling modules of the present invention may include fluid collection and fluid discharge manifolds that may be configured and arranged to target specific regions of an immersion bath that might otherwise become relatively stagnant, thereby enhancing overall system circulation and convective environment  …


**Key facts:** microjets ✓; nozzle ✓

---

## r22 (lookup) [ ] checked

**Q:** Which kinds of pumps can be used inside the immersion cooling module for electronics?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** electronics · "positive displacement pumps, centrifugal pumps and axial pumps" → 2 passage(s)

> *US12563707B2.txt, summary:* Furthermore, both the inlets and the outlets to the pump are designed to selectively enhance cooling of other components within the electronics assembly and avoid the creation of dead flow regions and the associated deviations in component temperatures.  [0013] The cooling module structure itself uses the pump to pressurize the inlet flow into a plenum that supplies immersion fluid to the micro-convective nozzle array. An outlet on the opposite side of the microconvective nozzle array(s) from the plenum then allows the immersion fluid to flow out of the cooling module to be dispersed in the immersion fluid of the immersion bath.  [0014] Several types of pumps can be used in implementations of the present invention, including without limitation, positive displacement pumps, centrifugal pumps and axial pumps. In each case, the seal and lubrication requirements for the integrated pump can be relaxed, taking advantage of the lubricating properties of the coolant and the fact that minor leakage is acceptable in an immersion environment, so long as the leakage is not so great as to undermine or prevent the pressurization of the immersion fluid inside the plenum or the acceleration and hi …

> *US12563707B2.txt, description:* [0036] A variety of different types of pumps and pump designs may be used to carry out the functions of the pump 115 in embodiments of the present invention, including without limitation, positive displacement pumps, centrifugal pumps and axial pumps. Other types of pumps, may be suitably adapted to use in implementations of the present invention, depending on the specific requirements and objectives of the immersion cooling system.  [0037] The overall heat-transfer performance and cooling capacity of an immersion cooling system may not reach its full potential if the immersion fluid 160 in some regions of the immersion bath tank 159 become relatively stagnant, leading to those regions becoming warm and/or producing hot spots in or on certain components. If electronic devices are located in these warm or hotspots, it could reduce their performance or lifespans. To address this potential problem, in some embodiments of the present invention, and as shown in FIG. 2 , the cooling module 100 further comprises one or more fluid collection manifolds 135 that are fluidly coupled to the inlet 137 of the cooling module 100, and one or more discharge manifolds 140 that are fluidly coupled to …


**Key facts:** centrifugal ✓

---

## m01 (multi_passage) [ ] checked

**Q:** How does the free-oscillation method obtain the resonant frequency and Q-factor, and what charging voltage might be applied to the capacitor?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** qfactor · abstract → 2 passage(s)

> *US10804750B2.txt, abstract:* A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor from monitoring the voltage.  RELATED DOCUMENTS  [0001] This application claims priority to U.S. Provisional Patent Application 62/546,988, filed on Aug. 17, 2017, which is herein incorporated by reference in its entirety.

> *US10804750B2.txt, summary:* [0006] In accordance with some embodiments of the present invention, a wireless power transmitter that measures the Q-factor is provided. In accordance with some embodiments, the wireless power transmitter includes a transmit coil; a capacitor coupled in series with the transmit coil to form a resonant circuit; a bridge circuit coupled to the resonant circuit; a control circuit coupled to control the bridge circuit to provide voltages across the resonant circuit; a charging circuit coupled to charge the capacitor with a charging voltage and coupled to be controlled by the control circuit; and a detection circuit coupled to receive a voltage across the capacitor and provide data related to the voltage to the control circuit while the resonant circuit.  [0007] A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor  …


**Label:** qfactor · "charging voltage Va from transmit control circuit 402 can be a 1.8V" → 1 passage(s)

> *US10804750B2.txt, description:* [0051] In some embodiments, a simpler calculation can be performed in step 444. If, instead of using a time T, the number of oscillations required such that Venv is approximately V0/2, then T=N/f0 and the above equation for Q becomes  [0052] Q ≅ π ⁢ ⁢ N ln ⁡ ( 2 ) ≅ 4.532 ⁢ ⁢ N . Consequently, Q can be calculated by counting the number of oscillations of Vcp(t) until the peak value of Vcp(t) becomes V0/2 and then multiplying that number by 4.532. Although losing some accuracy with this method, the resulting process can be very quick.  [0053] As discussed above, wireless power transmitter 400 as illustrated FIG. 4A can facilitate a method of determining the Q-factor Q as well as the resonant frequency f0. In some embodiments, for example, the charging voltage Va from transmit control circuit 402 can be a 1.8V output from transmitter control circuit 402. Transistors Q5 406, Q6 408 and Resistor R1 414 then form a circuit to charge Cp to about 1.8V at the initiation of a Q-factor detection process 430 as illustrated in FIG. 4B.  [0054] Transmit coil Lp 106, capacitor Cp 114, transistor Q3 208, and transistor Q4 210 form a free running resonant circuit during Q-factor detection. Frequen …


**Key facts:** 1.8V ✓; resonant frequency ✓

---

## m02 (multi_passage) [ ] checked

**Q:** How does the charger with a separate sensing coil cope with interference from a nearby charger, and how does it choose when to run detection?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sensing_coil · abstract → 1 passage(s)

> *US11316383B1.txt, abstract:* A wireless power system has a wireless power transmitting device and a wireless power receiving device. The wireless power transmitting device uses a wireless power transmitting coil to transmit wireless power signals to the wireless power receiving device during wireless power transmission periods. During alternating foreign object detection periods, the wireless power transmitting device gathers signals from the wireless power transmitting coil to detect foreign objects. Another wireless power transmitting device may transmit signals that can cause interference. To help reduce interference, the wireless power transmitting device gathers signals with a sensing coil that is separate from the wireless power transmitting coil and subtracts these signals from signals gathered with the wireless power transmitting coil. A signal quality metric may be used in adjusting the timing of the foreign object detection periods to help avoid interference from the other wireless power transmitting device.  [0001] This application claims the benefit of provisional patent application No. 62/946,044, filed Dec. 10, 2019, which is hereby incorporated by reference herein in its entirety.


**Label:** sensing_coil · "adjust the timing of periods TP" → 1 passage(s)

> *US11316383B1.txt, description:* [0047] To help enhance measurement accuracy by device 12 during foreign object detection periods TP, device 12 can evaluate the quality of the foreign object detection measurements being made by device 12. Device 12 can then adjust the timing of periods TP (e.g., start and end times for each period TP) so that these periods tend to coincide with low-noise time periods such as periods TP′.  [0048] A flow chart of illustrative operations involved in using system 8 in a configuration in which device 12 evaluates the quality of foreign object detection measurements so that the timing of foreign object detection measurements can be adjusted to enhance measurement quality is shown in FIG. 11.  [0049] During the operations of block 11, the control circuitry of device 12 operates device 12 with default settings. For example, device 12 may initially be configured so that periods TP of about 100 microseconds (e.g., at least 10 microseconds, at least 50 microseconds, less than 1000 microseconds, less than 500 microseconds, etc.) alternate with periods TN of at least 10 ms, at least 100 ms, at least 1 s, at least 10 s, less than 20 s, less than 2 s, less than 200 ms, less than 20 ms, or less t …


**Key facts:** sensing coil ✓; timing ✓

---

## m03 (multi_passage) [ ] checked

**Q:** What must the off-board charging station know about the vehicle's coolant before a rapid recharge, and why?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** offboard · "first determines the type of coolant" → 1 passage(s)

> *US20170297431A1.txt, description:* In this embodiment, the valve 110 is a three-way valve but could be any valve capable of shutting off the flow from the on-board system and allowing the off-board coolant to enter. In this embodiment, the off-board coolant is the same as on-board the vehicle.  [0016] The coolant passes through the battery pack 106 at the higher flow rate enabled by the off-board pump. After passing through the battery pack 106, the coolant returns to the off-board reservoir (e.g., source 64 in FIG. 3) via an outlet valve 112, which in this embodiment is a 3-way valve. Additionally, embodiments of the invention include the possibility of having multiple inlet and outlet valves. Having a greater number of valves may reduce the thermal gradient within the battery pack.  [0017] There are many important parameters to determine and control the maximum rate of charge that an electric vehicle can accept. The off-board system first determines the type of coolant which is on-board the vehicle. This can be determined via database from the vehicle owner's manual. Once it gets this information, then it can tap into a database which has all of the coolant properties, such as heat transfer coefficients, density a …


**Label:** offboard · "determining a type of coolant in a coolant loop" → 2 passage(s)

> *US20170297431A1.txt, summary:* [0004] In accordance with a first feature of the present invention, a method of providing coolant to an electric battery for powering a drive train of an electric vehicle is provided that includes providing coolant from a coolant source off-board the electric vehicle at a first rate to cool the electric battery during recharging of the electric battery; and circulating coolant through a coolant loop on-board the electric vehicle at a second rate less than the first rate to cool the electric battery after the recharging of the electric battery.  [0005] In accordance with a second feature of the present invention, a method of providing coolant to an electric battery for powering a drive train of an electric vehicle is provided that includes providing coolant from an off-board coolant source to an on-board coolant loop for cooling the electric battery as a function of parameters of the on-board coolant loop.  [0006] In accordance with a third feature of the present invention, a method of providing coolant to an electric battery for powering a drive train of an electric vehicle is provided that includes determining a type of coolant in a coolant loop on-board the electric vehicle in fl …

> *US20170297431A1.txt, claim 9:* 9. A method of providing coolant to an electric battery for powering a drive train of an electric vehicle comprising: determining a type of coolant in a coolant loop on-board the electric vehicle in heat transfer with the electric battery; selecting the determined type of coolant from a plurality of off-board coolant sources; and providing the determined type of coolant from an off-board coolant source to the coolant loop on-board the electric vehicle.


**Key facts:** type of coolant ✓

---

## m04 (multi_passage) [ ] checked

**Q:** What trip information does the predictive battery thermal management system use, and what can it do if no cooling or heating is needed?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** predictive · abstract → 1 passage(s)

> *US20190315232A1.txt, abstract:* A thermal management system of a battery of an electric vehicle proactively manages the temperature of the battery based on sensor data and sets limits to control cooling and heating of the battery. Using the data gathered from an autonomous drive platform, a highly-efficient control system which uses predictive modelling can be created. A control system predicts the battery final temperature and determines if cooling and/or heating is necessary for the route. If cooling and/or heating is not necessary, the thermal management system may be simply turned off to save energy. This is a dynamic approach which should optimize energy usage under all situations using trip predictive information (from GPS, route-calculation algorithms, and weather information), and thermal model predictive controls to determine battery final temperatures.


**Label:** predictive · "trip duration, weather, expected route" → 1 passage(s)

> *US20190315232A1.txt, description:* [0032] What is needed is a highly-efficient battery thermal management control scheme. In some embodiments, a predictive model may be created. Data gathered from an autonomous drive platform of a BEV may be used to update such a model during a trip. A control scheme may be capable of predicting a temperature battery at an upcoming end of a trip. Using the predicted battery temperature, a decision may be made by a processor of an onboard battery management system as to whether active cooling is necessary for the route. If it is determined that cooling is not necessary, the cooling system may simply be turned off, and energy may be saved.  [0033] Embodiments of the present disclosure may include the use of vehicle characterization data, combined with data from a network location associated with a current operating scenario. Data used may include information such as trip duration, weather, expected route, for example from GPS, route-calculating algorithms, and weather information. Using such data, the final state of the battery may be predicted. Such a dynamic approach may optimize energy usage under all situations. Some embodiments include one or both of active warming and cooling sy …


**Key facts:** weather ✓; turned off ✓

---

## m05 (multi_passage) [ ] checked

**Q:** Why does the thermal management controller use chiller outlet pressure and temperature, and which components does it adjust?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** pid_chiller · "fully vaporized battery refrigerant" → 1 passage(s)

> *US20230415612A1.txt, description:* This second error value (u2) is minimized by the second PID controller 804 by adjusting and optimizing a second output variable (v2). Stated differently, control logic 800 may calculate, using second PID controller 804, the second output variable (v2) using the second error value (u2). The EXV position command (Vpos,EXVx) is finally calculated from the second output variable (v2), for example using either a lookup table or a polynomial expression. Stated differently, control logic 800 may calculate an electronic expansion valve position command (Vpos,EXVx) based upon the second output variable (v2). Each expansion valve 268 may be commanded to the same position to avoid uneven mass flow rate, pressure, and temperature at the outlet of each chiller 250. The thermal management system 106 may command the expansion valve 268 to operate at the electronic expansion valve position command (Vpos,EXV1 and Vpos,EXV2) calculated using control logic 800.  [0068] In order to ensure that the battery refrigerant enters compressor 262 as a fully vaporized battery refrigerant, control logic 600 and/or control logic 800 may utilize chiller outlet pressure and temperature feedback to control the spee …


**Label:** pid_chiller · abstract → 1 passage(s)

> *US20230415612A1.txt, abstract:* The present disclosure provides a method of managing thermal loads in an electric vehicle and controlling various electronic components of a thermal management system. The method may comprise heating a battery coolant of a battery coolant loop utilizing waste heat from a battery to form a heated battery coolant, heating a refrigerant of a battery refrigeration loop by exchanging heat with the heated battery coolant, and measuring refrigerant temperature(s) and pressure(s) at an output of a chiller. The measured temperature(s) and pressure(s) may be utilized by the thermal management system as feedback signals for performing a proportional-integral-derivative control to compute an electronic expansion valve position command. Battery temperature(s) and/or battery coolant temperature(s) may be measured and utilized by the thermal management system as feedback signals for computing a pump speed command and performing a proportional-integral-derivative control to compute a compressor speed command and a condenser fan speed command.  CROSS-REFERENCE TO RELATED APPLICATIONS  [0001] This application claims priority to, and the benefit of, U.S. Provisional Patent Application Ser. No. 63/494 …


**Key facts:** compressor ✓; expansion valve ✓

---

## c01 (claim_explanation) [ ] checked

**Q:** Which circuits does claim 1 require in the wireless power transmitter?

Selected documents: US10804750B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** qfactor · claim 1 → 1 passage(s)

> *US10804750B2.txt, claim 1:* 1. A wireless power transmitter, comprising: a transmit coil, the transmit coil configured to transmit wireless power; a capacitor coupled in series with the transmit coil to form a resonant circuit between a first node at the transmit coil and a second node at the capacitor, the transmitter coil and the capacitor being coupled at a third node; a bridge circuit coupled to the first node and the second node of the resonant circuit; a charging circuit coupled to the third node and configured to charge the capacitor with a charging voltage; and a detection circuit coupled to the third node to receive a voltage across the capacitor and provide data related to the voltage; a control circuit coupled to the bridge circuit, the charging circuit, and the detecting circuit, wherein the control circuit controls the bridge circuit to provide current through the transmit coil to provide wireless power, and further wherein the control circuit determines a Q-factor by controlling the bridge circuit to ground the second node and disconnect the first node, controlling the charging circuit to charge the capacitor when the second node is grounded, when the capacitor is charged controlling the bridge  …


**Key facts:** charging circuit ✓; detection circuit ✓

---

## c02 (claim_explanation) [ ] checked

**Q:** What does claim 17 add?

Selected documents: US9178361B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** fod_coils · claim 17 → 1 passage(s)

> *US9178361B2.txt, claim 17:* 17. The system of claim 15, wherein the detection circuitry detects a foreign object based on a change in the Q-factor of the resonant circuit.


**Key facts:** Q-factor ✓

---

## c03 (claim_explanation) [ ] checked

**Q:** According to claim 19, when is foreign object detection carried out?

Selected documents: US9178361B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** fod_coils · claim 19 → 1 passage(s)

> *US9178361B2.txt, claim 19:* 19. The system of claim 15, wherein the detection circuitry detects a foreign object only when the power transmitter coil is not transmitting power.


**Key facts:** not transmitting ✓

---

## c04 (claim_explanation) [ ] checked

**Q:** Which cooling loops and valves does claim 1 require?

Selected documents: US11214114B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** parallel_loops · claim 1 → 1 passage(s)

> *US11214114B2.txt, claim 1:* 1. A thermal management system for a vehicle comprising: a traction battery for propelling the vehicle; a motor coupled to the traction battery; a first cooling loop circulating fluid to cool the traction battery; and a second cooling loop circulating fluid to cool the traction motor; a third loop for regulating a passenger cabin temperature and selectively coupled to the first and second cooling loops; and a radiator selectively in communication with the first cooling loop and second cooling loop, wherein the first loop, the second loop are in fluid communication and arranged in parallel to be cooled by the radiator, a radiator valve for selectively controlling fluid flow through the radiator, wherein in a first position fluid flows through the radiator and in a second position fluid bypasses the radiator, a battery valve for selectively controlling fluid flow through the traction battery, wherein when the radiator valve is in a first position, fluid flows through the radiator and when the battery valve is in a first position fluid flows in parallel through the first loop and the second loop, the radiator thereby cooling the battery and the traction motor in parallel.


**Key facts:** radiator valve ✓; battery valve ✓

---

## c05 (claim_explanation) [ ] checked

**Q:** What is in the second leg of the refrigerant loop in claim 1?

Selected documents: US20090249807A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** hvac_chiller · claim 1 → 1 passage(s)

> *US20090249807A1.txt, claim 1:* 1. A HVAC and battery thermal system for a vehicle having a passenger cabin and a battery pack, the system comprising: a refrigerant loop including a compressor, a condenser, a first leg and a second leg, the first leg including an evaporator expansion device and an evaporator configured to provide cooling to the passenger cabin, and the second leg including a battery expansion device and a chiller; and a coolant loop configured to direct a coolant through the battery pack and including a controllable coolant routing valve, a bypass branch and a chiller branch, the chiller being located in the chiller branch, and the coolant routing valve having a bypass outlet that directs the coolant into the bypass branch and a chiller outlet that directs the coolant into the chiller branch and through the chiller.


**Key facts:** chiller ✓; battery expansion device ✓

---

## c06 (claim_explanation) [ ] checked

**Q:** Where is the dielectric fluid located according to claim 1, and what heats and cools it?

Selected documents: US8852772B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** sealed · claim 1 → 1 passage(s)

> *US8852772B2.txt, claim 1:* 1. A vehicle battery pack with a self-contained liquid cooling system comprising: a sealed container having an interior space; a battery assembly disposed within the interior space of the container, the battery assembly including a plurality of battery cells having at least one fluid channel formed therebetween; a dielectric fluid disposed within the at least one fluid channel in contact with the battery cells of the battery assembly and configured to heat and cool the battery assembly; a heating element disposed within the interior space configured to heat the dielectric fluid; and a cooling element disposed within the interior space configured to cool the dielectric fluid.


**Key facts:** fluid channel ✓; heating element ✓; cooling element ✓

---

## c07 (claim_explanation) [ ] checked

**Q:** Explain what claim 1 of this patent covers.

Selected documents: US20250079567A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** runners · claim 1 → 1 passage(s)

> *US20250079567A1.txt, claim 1:* 1. A traction battery pack, comprising: a first battery module including a first interior volume; and an immersion cooling system for thermally managing the first battery module, wherein the immersion cooling system includes an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and the first interior volume, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume.


**Key facts:** intake manifold ✓; exhaust manifold ✓

---

## c08 (claim_explanation) [ ] checked

**Q:** What does claim 1 of this document require?

Selected documents: US20230369708A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** grouped · claim 1 → 1 passage(s)

> *US20230369708A1.txt, claim 1:* 1. An immersion cooling system for a battery system, comprising: a battery enclosure; G battery cell groups arranged in the battery enclosure, wherein each of the G battery cell groups include C battery cells, where G and C are integers greater than one; a plurality of dividers arranged between each of the G battery cell groups; and a gas manifold configured to receive vent gases from each of the G battery cell groups.


**Key facts:** dividers ✓; gas manifold ✓

---

## c09 (claim_explanation) [ ] checked

**Q:** In claim 1, what happens when the probability value exceeds the threshold?

Selected documents: US20190074730A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** ml_fod · claim 1 → 1 passage(s)

> *US20190074730A1.txt, claim 1:* 1. A wireless power transmitting device with a charging surface configured to receive a wireless power receiving device that has a wireless power receiving coil, the wireless power transmitting device comprising: a plurality of coils; wireless power transmitting circuitry coupled to the plurality of coils and configured to transmit wireless power signals with the plurality of coils; and control circuitry configured to: gather measurements from one or more coils of the plurality of coils; determine, using the measurements, a probability value indicative of whether a wireless power receiving device that has a wireless power receiving coil is present on the charging surface; and in accordance with determining that the probability value exceeds a threshold, cause the wireless power transmitting circuitry to transmit wireless power signals with one or more coils of the plurality of coils.


**Key facts:** transmit wireless power ✓

---

## p01 (patent_lookup) [ ] checked

**Q:** What does claim 1 of US11316383B1 require?

Expected intent `patent_lookup`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** sensing_coil · claim 1 → 1 passage(s)

> *US11316383B1.txt, claim 1:* 1. A wireless power transmitting device for transmitting wireless power to a wireless power receiving device in the presence of an additional wireless power transmitting device, comprising: wireless power transmitting circuitry having a wireless power transmitting coil configured to transmit wireless power signals to the wireless power receiving device; a sensing coil; and control circuitry configured to detect foreign objects using the wireless power transmitting coil while using the sensing coil to reduce interference from the additional wireless power transmitting device.


**Key facts:** sensing coil ✓

---

## p02 (patent_lookup) [ ] checked

**Q:** What is the main idea of US20160079633A1?

Expected intent `patent_lookup`, tools `['retrieve_evidence']`  

**Label:** kalman · abstract → 1 passage(s)

> *US20160079633A1.txt, abstract:* System and methods for estimating a temperature of a battery are presented. In some embodiments, a method of estimating a temperature of a battery system may utilize measured battery system temperature data and measured ambient temperature data. Based on the measured temperature data, an average estimated temperature of the battery system may be determined using, at least in part, an extended Kalman filter and an energy balance process model associated with the battery system.


**Key facts:** Kalman ✓

---

## p03 (patent_lookup) [ ] checked

**Q:** What does the receiver send to the transmitter in US11646607B2 to support foreign object detection?

Expected intent `patent_lookup`, tools `['retrieve_evidence']`  

**Label:** peak_freq · abstract → 1 passage(s)

> *US11646607B2.txt, abstract:* A wireless power receiver including a transmitter configured to transmit to a wireless power transmitter, a foreign object detection status packet including a mode bit field indicating whether a foreign object detection status packet includes a reference peak frequency of the wireless power receiver, in which the reference peak frequency is pre-assigned to the wireless power receiver; and a receiver configured to receive from the wireless power transmitter, a response indicating the foreign object is present or not present in a charging area of the wireless power transmitter, wherein the response is determined based on a comparison of a measured peak frequency of a power signal transmitted by the wireless power transmitter and an adaptable threshold frequency adapted based on the reference peak frequency included in the foreign object detection status packet from the wireless power receiver.  CROSS-REFERENCE TO RELATED APPLICATIONS  [0001] This Application is a Continuation of U.S. patent application Ser. No. 16/314,559 filed on Dec. 31, 2018 (now U.S. Pat. No. 11,070,095 issued on Jul. 20, 2021), which is the National Phase of PCT International Application No. PCT/KR2017/006975 fi …


**Label:** peak_freq · claim 1 → 1 passage(s)

> *US11646607B2.txt, claim 1:* 1. A wireless power receiver, comprising: a transmitter configured to transmit to a wireless power transmitter, a foreign object detection status packet including a mode bit field indicating whether a foreign object detection status packet includes a reference peak frequency of the wireless power receiver, wherein the reference peak frequency is pre-assigned to the wireless power receiver; and a receiver configured to receive from the wireless power transmitter, a response indicating the foreign object is present or not present in a charging area of the wireless power transmitter, wherein the response is determined based on a comparison of a measured peak frequency of a power signal transmitted by the wireless power transmitter and an adaptable threshold frequency adapted based on the reference peak frequency included in the foreign object detection status packet from the wireless power receiver.


**Key facts:** reference peak frequency ✓

---

## x01 (comparison) [ ] checked

**Q:** Compare how these two patents detect foreign objects on a wireless charger.

Selected documents: US10804750B2.txt, US20190074730A1.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** qfactor · abstract → 2 passage(s)

> *US10804750B2.txt, abstract:* A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor from monitoring the voltage.  RELATED DOCUMENTS  [0001] This application claims priority to U.S. Provisional Patent Application 62/546,988, filed on Aug. 17, 2017, which is herein incorporated by reference in its entirety.

> *US10804750B2.txt, summary:* [0006] In accordance with some embodiments of the present invention, a wireless power transmitter that measures the Q-factor is provided. In accordance with some embodiments, the wireless power transmitter includes a transmit coil; a capacitor coupled in series with the transmit coil to form a resonant circuit; a bridge circuit coupled to the resonant circuit; a control circuit coupled to control the bridge circuit to provide voltages across the resonant circuit; a charging circuit coupled to charge the capacitor with a charging voltage and coupled to be controlled by the control circuit; and a detection circuit coupled to receive a voltage across the capacitor and provide data related to the voltage to the control circuit while the resonant circuit.  [0007] A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor  …


**Label:** ml_fod · abstract → 1 passage(s)

> *US20190074730A1.txt, abstract:* A wireless power transmission system has a wireless power receiving device with a wireless power receiving coil that is located on a charging surface of a wireless power transmitting device with a wireless power transmitting coil array. Control circuitry in the wireless power transmitting device may use inverter circuitry to supply alternating-current signals to coils in the coil array, thereby transmitting wireless power signals. The control circuitry may also be used to detect foreign objects on the coil array such as metallic objects without wireless power receiving coils. For example, control circuitry may use inductance measurements from the coils in the coil array to determine a probability value indicative of whether a foreign object is present on the charging surface. The control circuitry may compare the probability value to a threshold and take suitable action in response to the comparison.  [0001] This application claims the benefit of provisional patent application No. 62/554,426, filed on Sep. 5, 2017, which is hereby incorporated by reference herein in its entirety.


---

## x02 (comparison) [ ] checked

**Q:** What are the differences between these two documents in how they estimate or predict battery temperature?

Selected documents: US20160079633A1.txt, US20190315232A1.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** kalman · abstract → 1 passage(s)

> *US20160079633A1.txt, abstract:* System and methods for estimating a temperature of a battery are presented. In some embodiments, a method of estimating a temperature of a battery system may utilize measured battery system temperature data and measured ambient temperature data. Based on the measured temperature data, an average estimated temperature of the battery system may be determined using, at least in part, an extended Kalman filter and an energy balance process model associated with the battery system.


**Label:** predictive · abstract → 1 passage(s)

> *US20190315232A1.txt, abstract:* A thermal management system of a battery of an electric vehicle proactively manages the temperature of the battery based on sensor data and sets limits to control cooling and heating of the battery. Using the data gathered from an autonomous drive platform, a highly-efficient control system which uses predictive modelling can be created. A control system predicts the battery final temperature and determines if cooling and/or heating is necessary for the route. If cooling and/or heating is not necessary, the thermal management system may be simply turned off to save energy. This is a dynamic approach which should optimize energy usage under all situations using trip predictive information (from GPS, route-calculation algorithms, and weather information), and thermal model predictive controls to determine battery final temperatures.


---

## x03 (comparison) [ ] checked

**Q:** Compare the immersion cooling designs of these two patents.

Selected documents: US8852772B2.txt, US20250079567A1.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** sealed · claim 1 → 1 passage(s)

> *US8852772B2.txt, claim 1:* 1. A vehicle battery pack with a self-contained liquid cooling system comprising: a sealed container having an interior space; a battery assembly disposed within the interior space of the container, the battery assembly including a plurality of battery cells having at least one fluid channel formed therebetween; a dielectric fluid disposed within the at least one fluid channel in contact with the battery cells of the battery assembly and configured to heat and cool the battery assembly; a heating element disposed within the interior space configured to heat the dielectric fluid; and a cooling element disposed within the interior space configured to cool the dielectric fluid.


**Label:** runners · claim 1 → 1 passage(s)

> *US20250079567A1.txt, claim 1:* 1. A traction battery pack, comprising: a first battery module including a first interior volume; and an immersion cooling system for thermally managing the first battery module, wherein the immersion cooling system includes an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and the first interior volume, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume.


---

## x04 (comparison) [ ] checked

**Q:** Contrast the cooling loop architectures described in these two documents.

Selected documents: US20090249807A1.txt, US11214114B2.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** hvac_chiller · claim 1 → 1 passage(s)

> *US20090249807A1.txt, claim 1:* 1. A HVAC and battery thermal system for a vehicle having a passenger cabin and a battery pack, the system comprising: a refrigerant loop including a compressor, a condenser, a first leg and a second leg, the first leg including an evaporator expansion device and an evaporator configured to provide cooling to the passenger cabin, and the second leg including a battery expansion device and a chiller; and a coolant loop configured to direct a coolant through the battery pack and including a controllable coolant routing valve, a bypass branch and a chiller branch, the chiller being located in the chiller branch, and the coolant routing valve having a bypass outlet that directs the coolant into the bypass branch and a chiller outlet that directs the coolant into the chiller branch and through the chiller.


**Label:** parallel_loops · claim 1 → 1 passage(s)

> *US11214114B2.txt, claim 1:* 1. A thermal management system for a vehicle comprising: a traction battery for propelling the vehicle; a motor coupled to the traction battery; a first cooling loop circulating fluid to cool the traction battery; and a second cooling loop circulating fluid to cool the traction motor; a third loop for regulating a passenger cabin temperature and selectively coupled to the first and second cooling loops; and a radiator selectively in communication with the first cooling loop and second cooling loop, wherein the first loop, the second loop are in fluid communication and arranged in parallel to be cooled by the radiator, a radiator valve for selectively controlling fluid flow through the radiator, wherein in a first position fluid flows through the radiator and in a second position fluid bypasses the radiator, a battery valve for selectively controlling fluid flow through the traction battery, wherein when the radiator valve is in a first position, fluid flows through the radiator and when the battery valve is in a first position fluid flows in parallel through the first loop and the second loop, the radiator thereby cooling the battery and the traction motor in parallel.


---

## x05 (comparison) [ ] checked

**Q:** Compare these two documents - what is being cooled, and how?

Selected documents: US12563707B2.txt, US8852772B2.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** electronics · abstract → 1 passage(s)

> *US12563707B2.txt, abstract:* Embodiments of the present invention provide a cooling module for cooling heat-generating electronic devices in an immersion cooling system. The cooling module includes an integrated pump, which draws immersion fluid from the surrounding dielectric bath and drives it into a pressurized plenum to pressurize the coolant fluid and drive the pressurized coolant fluid through a nozzle plate containing a microconvective nozzle array. The array accelerates the fluid to produce a multiplicity of microjets that impinge on a surface of the heat-generating electronic device to be cooled. The effluent from the cooling module may be directed to flow into and wash over nearby heat-generating devices to help cool the nearby heat-generating devices. The effluent may also be directed to the inlets of daughter cooling modules attached to other heat-generating electronic devices. In some embodiments, cooling modules of the present invention may include fluid collection and fluid discharge manifolds that may be configured and arranged to target specific regions of an immersion bath that might otherwise become relatively stagnant, thereby enhancing overall system circulation and convective environment  …


**Label:** sealed · abstract → 1 passage(s)

> *US8852772B2.txt, abstract:* A Lithium Ion battery cooling system for use in a hybrid vehicle comprises a plurality of self-contained liquid cooling modules, each cooling module including a closed and sealed container having an interior space. Each cooling module includes a battery assembly disposed within the interior space of the container and a plurality of battery cells having at least one fluid channel formed therebetween for receiving a fluid therein. A dielectric fluid is disposed within the at least one fluid channel. The dielectric fluid substantially immerses and is in contact with the battery assembly to heat and cool the battery assembly. A heating element is disposed within the interior space and heats the dielectric fluid. A cooling element is disposed within the interior space and cools the dielectric fluid.


---

## u01 (unanswerable) [ ] checked

**Q:** What is the retail price of the machine-learning wireless charging pad?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u02 (unanswerable) [ ] checked

**Q:** Which car models use the extended Kalman filter battery temperature estimation in production?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u03 (unanswerable) [ ] checked

**Q:** How many charge cycles does the immersion-cooled traction battery pack with intake runners last?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u04 (unanswerable) [ ] checked

**Q:** Which smartphone models are compatible with the charger that uses a separate sensing coil?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* Hard negative - another patent mentions smartphones in general.

---

## u05 (unanswerable) [ ] checked

**Q:** How much does the combined HVAC and battery chiller system weigh?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u06 (unanswerable) [ ] checked

**Q:** What is the maximum wind speed a solar panel cleaning robot can operate in?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* Off-topic for the whole corpus.

---

## u07 (unanswerable) [ ] checked

**Q:** How many prismatic cells fit in one compartment of the electronics immersion cooling module?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* False premise - the electronics module cools chips, not battery cells.

---

## l01 (legal) [ ] checked

**Q:** Does the Q-factor detection patent infringe the claims of the detection-coil patent?

Selected documents: US10804750B2.txt, US9178361B2.txt  
Expected intent `compare`, tools `['compare_patents']`, legal flag True  

**Label:** qfactor · claim 1 → 1 passage(s)

> *US10804750B2.txt, claim 1:* 1. A wireless power transmitter, comprising: a transmit coil, the transmit coil configured to transmit wireless power; a capacitor coupled in series with the transmit coil to form a resonant circuit between a first node at the transmit coil and a second node at the capacitor, the transmitter coil and the capacitor being coupled at a third node; a bridge circuit coupled to the first node and the second node of the resonant circuit; a charging circuit coupled to the third node and configured to charge the capacitor with a charging voltage; and a detection circuit coupled to the third node to receive a voltage across the capacitor and provide data related to the voltage; a control circuit coupled to the bridge circuit, the charging circuit, and the detecting circuit, wherein the control circuit controls the bridge circuit to provide current through the transmit coil to provide wireless power, and further wherein the control circuit determines a Q-factor by controlling the bridge circuit to ground the second node and disconnect the first node, controlling the charging circuit to charge the capacitor when the second node is grounded, when the capacitor is charged controlling the bridge  …


**Label:** fod_coils · claim 1 → 1 passage(s)

> *US9178361B2.txt, claim 1:* 1. A wireless power charging system for charging a separate device having a power receiver coil, the wireless power charging system comprising: at least one power transmitter coil configured for transmitting power by inductive coupling to the power receiver coil in the separate device, the power transmitter coil characterized by a transmitter coil dimension that is a lateral dimension of the power transmitter coil; at least one foreign object detection (FOD) coil located proximate to the power transmitter coil and oriented to detect foreign objects that disturb the power transmission, the FOD coil characterized by a FOD coil dimension that is a lateral dimension of the FOD coil and that is smaller than the lateral dimension of the power transmitter coil, wherein the at least one FOD coil comprises two or more FOD coils, the at least one power transmitter coil comprises two or more power transmitter coils; and a controller configured to select power transmitter coils for activation based on which FOD coils have detected foreign objects.


*Notes:* Must not give a legal opinion; a technical comparison with a disclaimer is correct.

---

## l02 (legal) [ ] checked

**Q:** Is US20160079633A1 still valid and enforceable?

Expected intent `patent_lookup`, tools `['retrieve_evidence']`, legal flag True  

**Label:** kalman · abstract → 1 passage(s)

> *US20160079633A1.txt, abstract:* System and methods for estimating a temperature of a battery are presented. In some embodiments, a method of estimating a temperature of a battery system may utilize measured battery system temperature data and measured ambient temperature data. Based on the measured temperature data, an average estimated temperature of the battery system may be determined using, at least in part, an extended Kalman filter and an energy balance process model associated with the battery system.


*Notes:* Must decline the legal question; describing the technology with a disclaimer is acceptable.

---

## l03 (legal) [ ] checked

**Q:** Would building the grouped-cell immersion system violate the claims of the other selected patent?

Selected documents: US20230369708A1.txt, US20250079567A1.txt  
Expected intent `compare`, tools `['compare_patents']`, legal flag True  

**Label:** grouped · claim 1 → 1 passage(s)

> *US20230369708A1.txt, claim 1:* 1. An immersion cooling system for a battery system, comprising: a battery enclosure; G battery cell groups arranged in the battery enclosure, wherein each of the G battery cell groups include C battery cells, where G and C are integers greater than one; a plurality of dividers arranged between each of the G battery cell groups; and a gas manifold configured to receive vent gases from each of the G battery cell groups.


**Label:** runners · claim 1 → 1 passage(s)

> *US20250079567A1.txt, claim 1:* 1. A traction battery pack, comprising: a first battery module including a first interior volume; and an immersion cooling system for thermally managing the first battery module, wherein the immersion cooling system includes an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and the first interior volume, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume.


---
