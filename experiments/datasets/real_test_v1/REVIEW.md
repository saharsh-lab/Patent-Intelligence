# Review sheet: real_test_v1

53 questions. For each one, check: is the question clear and realistic? Do the passages below really answer it, and is any relevant passage missing (search the corpus for it)? Are the key facts correct and short? Is the expected behaviour right? Write changes into dataset.yaml and note them in `notes`. Reviewer initials: ______

## t01 (lookup) [ ] checked

**Q:** How can the Q-factor be estimated by simply counting oscillations of the capacitor voltage?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** qfactor · "counting the number of oscillations" → 1 passage(s)

> *US10804750B2.txt, description:* [0051] In some embodiments, a simpler calculation can be performed in step 444. If, instead of using a time T, the number of oscillations required such that Venv is approximately V0/2, then T=N/f0 and the above equation for Q becomes  [0052] Q ≅ π ⁢ ⁢ N ln ⁡ ( 2 ) ≅ 4.532 ⁢ ⁢ N . Consequently, Q can be calculated by counting the number of oscillations of Vcp(t) until the peak value of Vcp(t) becomes V0/2 and then multiplying that number by 4.532. Although losing some accuracy with this method, the resulting process can be very quick.  [0053] As discussed above, wireless power transmitter 400 as illustrated FIG. 4A can facilitate a method of determining the Q-factor Q as well as the resonant frequency f0. In some embodiments, for example, the charging voltage Va from transmit control circuit 402 can be a 1.8V output from transmitter control circuit 402. Transistors Q5 406, Q6 408 and Resistor R1 414 then form a circuit to charge Cp to about 1.8V at the initiation of a Q-factor detection process 430 as illustrated in FIG. 4B.  [0054] Transmit coil Lp 106, capacitor Cp 114, transistor Q3 208, and transistor Q4 210 form a free running resonant circuit during Q-factor detection. Frequen …


**Key facts:** V0/2 ✓

---

## t02 (lookup) [ ] checked

**Q:** Besides detecting foreign objects, what else can an array of small detection coils tell the charger?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** fod_coils · "determine the location of the foreign object" → 1 passage(s)

> *US9178361B2.txt, description:* As shown in FIG. 7, with the small detection coil, the value of Q2/Q1 increases much faster. In other words, the detection capability of such small detection coils diminishes faster with the increase of distance than a detection coil with larger radius. Therefore, for the purpose of detecting foreign objects, rather than friendly parasitic components located at further distance from the transmitter, smaller coils provide fewer false positive results because they are less likely to detect friendly parasitic components.  [0058] Another advantage of using an array of multiple small detection coils is that an array can be used to determine the location of the foreign object 520. The location can be determined by comparing the responses of each of the detection coils 504 in the array. Since the detection coils are smaller than the power transmitter coils, the location of the foreign objects can be determined with an accuracy that is better than the size of the power transmitter coils.  [0059] In some embodiments, the location of the foreign object is detected using an array of (partly) overlapping FOD coils. In other embodiments, using this location information, the transmitter can sele …


**Key facts:** location ✓

---

## t03 (lookup) [ ] checked

**Q:** Why is the coil-based foreign object detection preferably done while no power is being transferred?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** fod_coils · "operated preferably when there is no power being transferred" → 1 passage(s)

> *US9178361B2.txt, description:* FIG. 13( c) also shows the current flowing through Cdc and the voltage across it. Compared to the current and voltage waveform shown in FIG. 13( b), there is almost no current and voltage change in FIG. 13( c).  [0076] It should be noted that the described ‘pre-charge’ is not only applicable to the detection method using decay in a resonant circuit. Indeed, for any other detection method which detects the power loss or power dissipation in the foreign objects, such ‘pre-charge’ can be used, and with the advantage of separating the power loss in foreign objects and receiver circuit.  [0077] The described foreign object detection approach is operated preferably when there is no power being transferred from transmitter to receiver (or vice versa), because the proposed foreign object detection process may have difficulty to differentiate between the transferred power and the power dissipation in a foreign object. One approach is to temporarily suspend the power transfer during execution of the foreign object detection process.  [0078] For example, either the transmitter or the receiver could request such timeout by sending a specific command. This could be, for example, a power interru …


**Label:** fod_coils · claim 19 → 1 passage(s)

> *US9178361B2.txt, claim 19:* 19. The system of claim 15, wherein the detection circuitry detects a foreign object only when the power transmitter coil is not transmitting power.


**Key facts:** suspend ✓

---

## t04 (lookup) [ ] checked

**Q:** Why can a second charger nearby make the Q factor measurement unreliable?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sensing_coil · "create noise during foreign object detection periods" → 1 passage(s)

> *US11316383B1.txt, description:* By measuring signal resonating in coil 36 during each period TP, measurement circuitry 41 measures decay envelope 100 and thereby determines the value of Q. This Q-factor value and, if desired, information on the frequency of the coil signal during each period TP can be used to detect foreign objects. For example, the measured value of Q can be compared to a previously obtained baseline Q value. If a change in Q is detected (e.g., a change that is greater in magnitude than a predetermined threshold), device 12 can conclude that a foreign object is present and can take appropriate action (e.g., by halting wireless power transmission).  [0037] In the presence of a simultaneously transmitted wireless power signal such as wireless power signal 44′ from nearby wireless power transmitting circuitry TX2, there is a potential for signals 44′ to be received by coil 36 and create noise during foreign object detection periods TP. This can make it challenging to accurately measure Q and detect foreign objects.  [0038] By measuring signals 44′ with a sensing coil, device 12 can subtract signals 44′ from the signals being measured on coil 36. FIG. 4 is a top view of device 12 in an illustrative  …


**Label:** sensing_coil · abstract → 1 passage(s)

> *US11316383B1.txt, abstract:* A wireless power system has a wireless power transmitting device and a wireless power receiving device. The wireless power transmitting device uses a wireless power transmitting coil to transmit wireless power signals to the wireless power receiving device during wireless power transmission periods. During alternating foreign object detection periods, the wireless power transmitting device gathers signals from the wireless power transmitting coil to detect foreign objects. Another wireless power transmitting device may transmit signals that can cause interference. To help reduce interference, the wireless power transmitting device gathers signals with a sensing coil that is separate from the wireless power transmitting coil and subtracts these signals from signals gathered with the wireless power transmitting coil. A signal quality metric may be used in adjusting the timing of the foreign object detection periods to help avoid interference from the other wireless power transmitting device.  [0001] This application claims the benefit of provisional patent application No. 62/946,044, filed Dec. 10, 2019, which is hereby incorporated by reference herein in its entirety.


**Key facts:** noise ✓

---

## t05 (lookup) [ ] checked

**Q:** Which everyday objects are given as examples of foreign objects in the patent that uses a reference peak frequency?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** peak_freq · "coins, clips, pins, and ballpoint pens" → 2 passage(s)

> *US11646607B2.txt, technical_field:* The electromagnetic resonance method is rarely influenced by electromagnetic waves and thus is advantageously safe for other electronic devices or human bodies. In contrast, this method may be used in a limited distance and space and energy transmission efficiency is somewhat low.  [0009] The short-wavelength wireless power transmission method (briefly, referred to as the RF transmission method) takes advantage of the fact that energy may be directly transmitted and received in the form of a radio wave. This technology is a RF wireless power transmission method using a rectenna. The rectenna is a combination of an antenna and a rectifier and means an element for directly converting RF power into DC power. That is, the RF method is technology of converting AC radio waves into DC. Recently, as efficiency of the RF method has been improved, studies into commercialization of the RF method have been actively conducted  [0010] Wireless power transmission technology may be used not only in mobile related industries but also in various industries such as IT, railroad and home appliance.  [0011] If a conductor which is not a wireless power receiver, that is, a foreign object (FO), is presen …

> *US11646607B2.txt, technical_field:* For example, the FO may include coins, clips, pins, and ballpoint pens.  [0012] If an FO is present between a wireless power receiver and a wireless power transmitter, wireless charging efficiency may be significantly lowered, and the temperatures of the wireless power receiver and the wireless power transmitter may increase due to increase in ambient temperature of the FO. If the FO located in the charging area is not removed, power waste may occur and the wireless power transmitter and the wireless power receiver may be damaged due to overheating.  [0013] Accordingly, accurate detection of the FO located in the charging area is becoming an important issue in wireless charging technology.


**Key facts:** clips ✓; ballpoint pens ✓

---

## t06 (lookup) [ ] checked

**Q:** Which kinds of sensors have previously been used to detect objects on electric vehicle wireless charging pads?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** impedance_fod · "thermistor sensors, thermal cameras, radar sensors" → 1 passage(s)

> *US20220115917A1.txt, background:* Thus, the variation in system parameters is used to detect the object. However, such a technology is not applicable for high-power applications such as wireless charging of electric vehicles. Additionally, misalignment between the transmitter and receiver coils may occur thus affecting system parameters and providing an incorrect indication of an object.  [0005] Another developed technology uses sensors to detect the object in the wireless power transfer area. For example, thermistor sensors, thermal cameras, radar sensors, and ultrasonic sensors have been used to detect objects. Other systems use temperature sensors to detect the temperature increase in the object due to the eddy current generation. However, the addition of sensors further increases the overall system costs.  [0006] Therefore, a technology development is required for improving the detection of objects in the area of a wireless power transfer.


**Key facts:** thermal cameras ✓; radar ✓

---

## t07 (lookup) [ ] checked

**Q:** Which hazards is object detection on the vehicle charging pad meant to prevent?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** impedance_fod · "harm to animals such as pets" → 1 passage(s)

> *US20220115917A1.txt, summary:* [0007] The present disclosure provides an inductive wireless power transfer system in which the presence of an object on a transmission pad is detected to prevent eddy currents, overheating of the object and surrounding structures, fire hazards, and harm to animals such as pets who may unwittingly place themselves into the electromagnetic field of the power transfer system.  [0008] In an exemplary embodiment, an inductive wireless power transfer system is provided. The inductive wireless power transfer system may include a receiver pad, a transmission pad, and a detection coil layer disposed on the transmission pad to detect an object disposed thereon. The transmission pad may be configured to generate an electromagnetic field to provide energy transfer to the receiver pad.  [0009] In an exemplary embodiment, the detection coil layer may include multi-layer detection coils and each multi-layer detection coil may include a particular number of detection coils. Each detection coil may include an inductor provided in series with a resistor. The detection coil layer may be a single layer that includes a plurality of detection coil sets and each detection coil set may include two detect …


**Key facts:** fire ✓; pets ✓

---

## t08 (lookup) [ ] checked

**Q:** Which measurements are gathered from each coil for the machine-learning foreign object detection?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** ml_fod · claim 6 → 1 passage(s)

> *US20190074730A1.txt, claim 6:* 6. The wireless power transmitting device of claim 1, wherein gathering measurements from one or more coils of the plurality of coils comprises gathering an inductance measurement and a quality factor measurement for each coil in the plurality of coils.


**Label:** ml_fod · "inductance measurements and other measurements" → 1 passage(s)

> *US20190074730A1.txt, summary:* [0004] A wireless power transmission system has a wireless power receiving device that is located on a charging surface of a wireless power transmitting device. The wireless power receiving device has a wireless power receiving coil and the wireless power transmitting device has a wireless power transmitting coil array. Control circuitry may use inverter circuitry in the wireless power transmitting device to supply alternating-current signals to coils in the coil array, thereby transmitting wireless power signals.  [0005] Signal measurement circuitry coupled to the coil array may make measurements while the control circuitry uses the inverter circuitry to apply excitation signals to each of the coils. The control circuitry can analyze measurements made with the signal measurement circuitry to determine the values of inductances and other measurements associated with the coils in the coil array.  [0006] Foreign objects on the coil array such as metallic objects without wireless power receiving coils can be detected using machine-learning-based foreign object detection. For example, control circuitry may use inductance measurements and other measurements from the coils in the coil ar …


**Key facts:** inductance ✓; quality factor ✓

---

## t09 (lookup) [ ] checked

**Q:** How much heat must the heat exchanger absorb during a 300 kW rapid recharge?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** offboard · "absorb the 50 or more kW of heat" → 1 passage(s)

> *US20170297431A1.txt, description:* Connector 42 may also include spring loaded couplings at or near heat exchange fluid supply section 84 that allow for quick sealing of supply section 84 during the removal of connector 42 from receptacle 50 to prevent heat exchange fluid leakage.  [0044] Embodiments of invention may include other recharging stations, including but not limited to home based recharging stations. These home based recharging stations could be specific to the type of vehicle being recharged by the user.  [0045] The recharging stations at home could withdraw current from the grid at a slower rate during off-hours to recharge an associated battery pack which would rapidly discharge to provide power to the vehicle to recharge its batteries.  [0046] One of the primary benefits of embodiments of the invention is the potential weight, cost, and volume savings associated with not needing to upgrade the electric vehicle's on-board system. An improved heat exchanger may be provided to accept higher rates of recharge. The heat exchanger may have a cooling capacity required to absorb the 50 or more kW of heat generated during a 300 kW recharge. Heat exchangers capable of handling a rate of 120 kW may also be used. …


**Key facts:** 50 ✓

---

## t10 (lookup) [ ] checked

**Q:** How thick are the on-board coolant pipes in the Tesla Model S example?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** offboard · "0.5 mm thick" → 2 passage(s)

> *US20170297431A1.txt, description:* The following is a sample calculation based on multiple parameters obtained from the database which determines the maximum flow velocity based on a given pump power.  [0000] W . h = ηρ   q .  gh l = ρ   qgf  L D  V 2 2  g = ηρ   V ( 0.00012   m 2 1 )  g  24  μ ρ   VD  L D  V 2 2  g = η   V ( 0.00012   m 2 1 )  12  μ D  L D  V  [0029] Now solving for velocity V:  [0000] V 2 = W . h  D 2 12  ημ   L  ( 0.00012   m 2 1 ) = 18.56   m 2 s 2  [0030] Using the values from above, as well as the pump efficiency η, solve for Vmax For now, assume the pump is 100% efficient.  [0000] V max=4.308 m/s  [0031] An alternative limiting factor in step 403 may be the maximum pressure which the pipes of the on-board cooling system can handle. In the case of the Tesla Model S for example, the pipes are made of some kind of metal, including but not limited to copper or aluminum, and are 0.5 mm thick. Using the flow velocity calculated above in step 403, the pressure within the tubing system can be determined.

> *US20170297431A1.txt, description:* In the case of the Tesla Model S for example, the pipes are made of some kind of metal, including but not limited to copper or aluminum, and are 0.5 mm thick. Using the flow velocity calculated above in step 403, the pressure within the tubing system can be determined.  [0000] P = ρ   gh = ( 1121   kg m 3 )  ( 9.8   m s 2 )  ( 140.85   m ) = 1.547   MPa P = 2  ( strength )  ( thickness ) ( D )  ( safety   factor ) P = 2  ( 33.3   MPa )  ( 0.0005   m ) ( 0.00706   m )  ( 1.5 ) = 3.14   MPa  [0000] In this particular case with a copper tube, the pipe burst pressure is above the maximum pressure due to the coolant flow rate. In other instances, this may not be the case and the maximum flow rate could be limited by this pressure.  [0032] In order to determine the necessary convective heat transfer coefficient 404, the database can access experimental research or a calculation can be used to derive the coefficient empirically. Other necessary heat transfer coefficients of the tubing materials may be accessed from the database in this stage.


**Key facts:** 0.5 mm ✓

---

## t11 (lookup) [ ] checked

**Q:** In which situations may a large electric vehicle battery still need active cooling?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** predictive · "high-speed driving, continual uphill driving" → 1 passage(s)

> *US20190315232A1.txt, background:* In some cases, the range of a BEV can be reduced by up to 10-15% due to poor thermal management of the battery. As such, the thermal management of a BEV battery should be minimized to maximize vehicle range.  [0006] As battery size and/or capacity of BEVs increase, the power requirement per-battery cell decreases. This reduces the amount of heat generated by the battery; thus, most driving conditions do not require cooling. However, for certain use cases such as high-speed driving, continual uphill driving, DC-fast charging, and hot climates, a battery may reach a threshold temperature and active cooling may be required.  [0007] Current battery thermal control schemes are reactive—sensor data and set limits are used to control cooling power to battery thermal management system. Typical conventional systems often focus on the overall control of the battery thermal management system based on known information about a vehicle, that is information gathered during the design phase of the vehicle, in which the system is characterized under a number of different situations. This results in a heuristic based approach which may lower energy usage in some situations; such an approach, howeve …


**Key facts:** uphill ✓; hot climates ✓

---

## t12 (lookup) [ ] checked

**Q:** Which two models are used in the prediction stage of the battery temperature estimate?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** kalman · "based on a process model and a measurement model" → 1 passage(s)

> *US20160079633A1.txt, summary:* The EKF may operate recursively on new temperature measurements received in a series of measurements and produce a battery system temperature estimate with increased accuracy. In certain embodiments, the EFK may be configured to operate in real time using new input temperature measurements and results derived based on previously received temperature measurements.  [0006] In certain embodiments, the EFK may utilize at least two computational stages: a predication stage and an update stage. In the prediction stage, a battery temperature may be estimated based on a process model and a measurement model. An uncertainty (e.g., a process error covariance) associated with the estimated temperature may also be predicted. The estimated temperature and predicted uncertainty may be passed to the update stage, where measurement uncertainty (e.g., a measurement error covariance) and a Kalman gain may be calculated, and the estimated temperature state measurement may be updated. This information may be provided to the prediction stage for recursive temperature estimation.  [0007] In some embodiments, a method for estimating the temperature of a battery system may include receiving battery system …


**Key facts:** process model ✓; measurement model ✓

---

## t13 (lookup) [ ] checked

**Q:** Does the battery temperature estimation software have to be written in a particular programming language?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** kalman · "independent of the programming language" → 1 passage(s)

> *US20160079633A1.txt, description:* [0050] Processor 502 may include one or more general purpose processors, application specific processors, programmable microprocessors, microcontrollers, digital signal processors, FPGAs, other customizable or programmable processing devices, and/or any other devices or arrangement of devices that are capable of implementing the systems and methods disclosed herein.  [0051] Processor 502 may be configured to execute computer-readable instructions stored on non-transitory computer-readable storage medium 510. Computer-readable storage medium 510 may store other data or information as desired. In some embodiments, the computer-readable instructions may include computer executable functional modules 514. For example, the computer-readable instructions may include one or more functional modules configured to implement all or part of the functionality of the systems and methods described above. Specific functional models that may be stored on computer-readable storage medium 510 may include a module configured to perform battery system temperature estimation methods and/or associated calculations consistent with embodiments disclosed herein, and/or any other module or modules configured …


**Key facts:** C++ ✓

*Notes:* Answer is "no particular language" (examples C, C++, Java...). Tests reading a boilerplate passage.

---

## t14 (lookup) [ ] checked

**Q:** How is the battery warmed when the cabin air conditioning is off in the combined HVAC and battery system?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** hvac_chiller · "battery warming (self-heating) is desired" → 1 passage(s)

> *US20090249807A1.txt, description:* The need for battery cooling and heating may be dependent upon ambient conditions, current electric power usage as well as the current battery temperature, which can be different than the current passenger cabin cooling (or heating) load.  [0018] For operating mode 1, the passenger cabin air conditioning is off (cabin cooling load 0) and battery cooling or heating is not currently needed (battery thermal load 0). In this operating mode, then, the compressor 28 is off, so no refrigerant will flow, and the coolant routing valve is set to direct coolant through the second output 66 (valve position 2) to the coolant bypass line 68.  [0019] For operating mode 2, the passenger cabin air conditioning is off and battery warming (self-heating) is desired. As with the first operating mode, the compressor 28 is off, and the coolant routing valve 58 is set to the second outlet 66 (valve position 2). A battery internal heater (not show) or other suitable heater, such as a coolant heater (not shown) in the coolant loop 50 may be employed to provide the battery warming.  [0020] For operating mode 3, the passenger cabin air conditioning is off and the vehicle 20 may be, for example, in electric op …


**Key facts:** heater ✓

---

## t15 (lookup) [ ] checked

**Q:** When is the traction battery cooled by the radiator without using the chiller?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** parallel_loops · "cooled by the radiator without the chiller" → 2 passage(s)

> *US11214114B2.txt, summary:* [0005] In one embodiment, an electric vehicle thermal management system is provided. The thermal management system includes a battery loop for regulating temperature of a traction battery. The battery loop includes a chiller adapted to cool fluid in the battery loop and a battery pump for circulating fluid in the battery loop. A motor loop is provided for regulating temperature of a traction motor and is in fluid communication with the battery loop. The motor loop includes a motor pump for circulating fluid in the motor loop. The motor pump and the battery pump are arranged in parallel. A radiator is n fluid communication with the battery loop and motor loop. A radiator valve selectively controls fluid flow through the radiator. When the radiator valve is in a first position, fluid flows through the radiator. When the radiator valve is in a second position, fluid bypasses the radiator. A battery valve selectively couples the battery loop and the motor loop. When the battery valve is in a first position, fluid flows in parallel through the battery loop and the motor loop. The traction battery is cooled by the radiator without the chiller when both the radiator valve and the battery  …

> *US11214114B2.txt, claim 3:* 3. The thermal management system of claim 1 further comprising a chiller adapted to cool fluid in the first loop, wherein the battery is cooled by the radiator without the chiller when the radiator valve is in the first position and the battery valve is in the first position.


**Key facts:** first position ✓

---

## t16 (lookup) [ ] checked

**Q:** What is the condenser fan speed command calculated from?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** pid_chiller · "calculating a condenser fan speed command using the compressor speed command" → 2 passage(s)

> *US20230415612A1.txt, summary:* [0008] In various embodiments, the method may further comprise calculating a condenser fan speed command using the compressor speed command, and controlling a speed of a condenser fan in the battery refrigeration loop based upon the condenser fan speed command. Calculating the compressor speed command using the difference and the normalized coolant flow rate may comprise multiplying the difference and the normalized coolant flow rate to obtain an error value, and performing a proportional-integral-derivative (PID) control using the error value to compute an output variable. The compressor speed command may be calculated using at least one of a lookup table or a polynomial expression. The condenser fan speed command may be calculated using at least one of a lookup table or a polynomial expression. The compressor speed command may be calculated further based upon a coolant flow rate, the normalized coolant flow rate determined based upon the coolant flow rate.  [0009] In various embodiments, the method further comprises calculating the coolant flow rate using at least one of a first measured battery temperature or a second measured battery temperature.  [0010] A thermal management sy …

> *US20230415612A1.txt, claim 9:* 9. The method of claim 8, further comprising: calculating a condenser fan speed command using the compressor speed command; and controlling a speed of a condenser fan in the battery refrigeration loop based upon the condenser fan speed command.


**Key facts:** compressor speed command ✓

---

## t17 (lookup) [ ] checked

**Q:** What conditions can cause a battery thermal event in the immersion-cooled traction battery pack?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** runners · "over-charging conditions, over-discharging conditions" → 2 passage(s)

> *US20250079567A1.txt, description:* It should therefore be understood that the control module 58 and one or more additional controllers operably coupled thereto can collectively be referred to as a “control module” within the scope of this disclosure.  [0054] The control module 58 may be programmed with executable instructions for interfacing with and commanding operation of various components of the immersion cooling system 32 as part of a control strategy for controlling a flow rate of the cooling fluid F through each individual battery module 22. The control module 58 may include a processor 60 and non-transitory memory 62 for executing the various control strategies and modes associated with the immersion cooling system 32. The processor 60 may be a custom made or commercially available processor, a central processing unit (CPU), or generally any device for executing software instructions. The memory 62 may include any one or combination of volatile memory elements and/or nonvolatile memory elements. The processor 60 may be operably coupled to the memory 62 and may be configured to execute one or more programs stored in the memory 62 based on the various inputs received from other devices (e.g., the temperature s …

> *US20250079567A1.txt, description:* A battery thermal event may occur, for example, during over-charging conditions, over-discharging conditions, or other conditions and can cause one or more of the battery cells 24 to expel battery vent byproducts which can include gases, effluent particles, and/or other vent byproducts.  [0056] The temperature sensors 56 may periodically provide input signals to the control module 58 that are indicative of the temperature of the cooling fluid F exiting each battery module 22. In response to receiving the input signals, the control module 58 may control operations of the pump 46 and the flow control valves 54 in order to achieve a desired flow rate of the cooling fluid F though each respective battery module 22. For example, when the temperature input signals for one of the respective battery modules 22 indicate a temperature that is below a first predefined temperature threshold (e.g., about 60 degrees C.), the control module 58 may command the pump 46 and the flow control valve 54 associated with that respective battery module 22 to operate in a manner appropriate for achieving a first or “low” flow rate. Notably, “low” flow rates could include zero flow through the respective bat …


**Key facts:** over-charging ✓

---

## t18 (lookup) [ ] checked

**Q:** How does the grouped-cell immersion cooling system stop thermal runaway from spreading to neighbouring cells?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** grouped · "prevents hot gas convection to neighboring battery cells" → 1 passage(s)

> *US20230369708A1.txt, description:* As a battery cell begins to fail, hot gas/particles are emitted by the battery cell. The hot gas/particles from the failed battery cell can cause heat transfer to other adjacent battery cells. As the adjacent battery cells are heated, they too can fail and cause further failures or propagation.  [0029] An immersion cooling system according to the present disclosure prevents hot gas from heating neighboring battery cells by separating the battery cells into battery cell groups, supplying dielectric fluid to the battery cell groups, and managing vent gas generated by each of the battery cell groups to prevent the vent gas from that battery cell group from causing further battery cell failures due to overheating. In other words, the immersion cooling system prevents hot gas convection to neighboring battery cells to prevent thermal runaway propagation. As will be described further below, the immersion cooling system utilizes edge cooling or both edge and face cooling to prevent thermal runaway propagation to neighboring battery cells.  [0030] The immersion cooling system according to the present disclosure has improved cooling performance that enables DC fast charging while protecting …


**Key facts:** hot gas ✓

---

## t19 (lookup) [ ] checked

**Q:** Where are the heating element and the cooling element placed inside the sealed battery container?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sealed · "located at a base area 36" → 1 passage(s)

> *US8852772B2.txt, description:* In another embodiment, the gap 24 may be less than 0.25 mm. It is understood that other gap sizes can be used as desired.  [p-0016] A dielectric coolant 28 is disposed within the interior space 16 of the container 14 and the fluid level shown is such that the battery assembly 18 is completely immersed within the dielectric coolant 28. The dielectric coolant 28 is in contact with the battery cells 20 through the fluid channels 26 formed by gaps 24. In one embodiment, the dielectric coolant 28 may be halogenated. In another embodiment, the dielectric coolant 28 may be conditioned to have a boiling point at or near a desired operating temperature of the battery cells 20.  [p-0017] A heating element 34 is located at a base area 36 of the container 14. The heating element 34 shown is an electronic heating element. It is understood that other heating element types may be used. The heating element 34 is shown as a single element; however, multiple heating elements 34 such as heating plates may be provided.  [p-0018] A cooling element 38 is located at an upper area 40 of the container 14. The cooling element 38 may be a chilled water condenser having an inlet 42 and an outlet 44 extending  …


**Label:** sealed · "located at an upper area 40" → 1 passage(s)

> *US8852772B2.txt, description:* In another embodiment, the gap 24 may be less than 0.25 mm. It is understood that other gap sizes can be used as desired.  [p-0016] A dielectric coolant 28 is disposed within the interior space 16 of the container 14 and the fluid level shown is such that the battery assembly 18 is completely immersed within the dielectric coolant 28. The dielectric coolant 28 is in contact with the battery cells 20 through the fluid channels 26 formed by gaps 24. In one embodiment, the dielectric coolant 28 may be halogenated. In another embodiment, the dielectric coolant 28 may be conditioned to have a boiling point at or near a desired operating temperature of the battery cells 20.  [p-0017] A heating element 34 is located at a base area 36 of the container 14. The heating element 34 shown is an electronic heating element. It is understood that other heating element types may be used. The heating element 34 is shown as a single element; however, multiple heating elements 34 such as heating plates may be provided.  [p-0018] A cooling element 38 is located at an upper area 40 of the container 14. The cooling element 38 may be a chilled water condenser having an inlet 42 and an outlet 44 extending  …


**Key facts:** base ✓; upper ✓

---

## t20 (lookup) [ ] checked

**Q:** What kind of device is used as the cooling element in the sealed liquid-cooled battery container?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sealed · "chilled water condenser" → 1 passage(s)

> *US8852772B2.txt, description:* In another embodiment, the gap 24 may be less than 0.25 mm. It is understood that other gap sizes can be used as desired.  [p-0016] A dielectric coolant 28 is disposed within the interior space 16 of the container 14 and the fluid level shown is such that the battery assembly 18 is completely immersed within the dielectric coolant 28. The dielectric coolant 28 is in contact with the battery cells 20 through the fluid channels 26 formed by gaps 24. In one embodiment, the dielectric coolant 28 may be halogenated. In another embodiment, the dielectric coolant 28 may be conditioned to have a boiling point at or near a desired operating temperature of the battery cells 20.  [p-0017] A heating element 34 is located at a base area 36 of the container 14. The heating element 34 shown is an electronic heating element. It is understood that other heating element types may be used. The heating element 34 is shown as a single element; however, multiple heating elements 34 such as heating plates may be provided.  [p-0018] A cooling element 38 is located at an upper area 40 of the container 14. The cooling element 38 may be a chilled water condenser having an inlet 42 and an outlet 44 extending  …


**Key facts:** chilled water condenser ✓

---

## t21 (lookup) [ ] checked

**Q:** Which electronic components is the immersion cooling module with an integrated pump designed to cool?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** electronics · "central processing units (CPUs), graphical processing units (GPUs)" → 1 passage(s)

> *US12563707B2.txt, technical_field:* [0001] The present invention relates generally to methods and devices for cooling high-powered heat-generating electronic devices, and more particularly to cooling modules and cooling assemblies for central processing units (CPUs), graphical processing units (GPUs), power converters and power inverters.  RELATED ART  [0002] Electronic devices, such as CPUs, GPUs, chip sets and power converters and power inverters produce considerable amounts of waste heat during operation. Because excessive waste heat and high temperatures inside and around such heat-generating devices tend to limit processing performance and reduce component lifespans, it is considered imperative to manage thermal loads of processors by removing and/or dissipating as much heat as possible as quickly as possible. A traditional method of moderating, removing and dissipating excess waste heat produced by heat-generating electronic devices involves using fan-cooled heat sinks to continuously force a coolant fluid, such as air, water or oil, to hit and pass over a surface of the heat-generating device. However, as heat-generating electronic components continue to get smaller (and more powerful), and printed circuit boa …


**Label:** electronics · claim 5 → 1 passage(s)

> *US12563707B2.txt, claim 5:* 5. The cooling module of claim 1, wherein the heat-generating electronic device attached to the printed circuit board comprises: (a) a central processing unit; or (b) a graphical processing unit; or (c) a component of a power inversion system; or (d) a component of a power conversion system; or (e) a combination of two or more of the above-listed devices.


**Key facts:** CPU ✓; GPU ✓

---

## t22 (lookup) [ ] checked

**Q:** Where can the fluid leaving one chip cooling module be sent next?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** electronics · "inlets of daughter cooling modules" → 1 passage(s)

> *US12563707B2.txt, abstract:* Embodiments of the present invention provide a cooling module for cooling heat-generating electronic devices in an immersion cooling system. The cooling module includes an integrated pump, which draws immersion fluid from the surrounding dielectric bath and drives it into a pressurized plenum to pressurize the coolant fluid and drive the pressurized coolant fluid through a nozzle plate containing a microconvective nozzle array. The array accelerates the fluid to produce a multiplicity of microjets that impinge on a surface of the heat-generating electronic device to be cooled. The effluent from the cooling module may be directed to flow into and wash over nearby heat-generating devices to help cool the nearby heat-generating devices. The effluent may also be directed to the inlets of daughter cooling modules attached to other heat-generating electronic devices. In some embodiments, cooling modules of the present invention may include fluid collection and fluid discharge manifolds that may be configured and arranged to target specific regions of an immersion bath that might otherwise become relatively stagnant, thereby enhancing overall system circulation and convective environment  …


**Key facts:** daughter ✓

---

## m01 (multi_passage) [ ] checked

**Q:** How does the charger with a separate sensing coil measure the Q factor, and when does it take that measurement?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** sensing_coil · claim 5 → 1 passage(s)

> *US11316383B1.txt, claim 5:* 5. The wireless power transmitting device of claim 1 wherein the control circuitry is configured to measure a quality factor of the wireless power transmitting coil to detect foreign objects.


**Label:** sensing_coil · claim 7 → 1 passage(s)

> *US11316383B1.txt, claim 7:* 7. The wireless power transmitting device of claim 6 wherein the control circuitry is configured to measure the quality factor of the wireless power transmitting coil during the foreign object detection periods.


**Label:** sensing_coil · abstract → 1 passage(s)

> *US11316383B1.txt, abstract:* A wireless power system has a wireless power transmitting device and a wireless power receiving device. The wireless power transmitting device uses a wireless power transmitting coil to transmit wireless power signals to the wireless power receiving device during wireless power transmission periods. During alternating foreign object detection periods, the wireless power transmitting device gathers signals from the wireless power transmitting coil to detect foreign objects. Another wireless power transmitting device may transmit signals that can cause interference. To help reduce interference, the wireless power transmitting device gathers signals with a sensing coil that is separate from the wireless power transmitting coil and subtracts these signals from signals gathered with the wireless power transmitting coil. A signal quality metric may be used in adjusting the timing of the foreign object detection periods to help avoid interference from the other wireless power transmitting device.  [0001] This application claims the benefit of provisional patent application No. 62/946,044, filed Dec. 10, 2019, which is hereby incorporated by reference herein in its entirety.


**Key facts:** quality factor ✓; detection periods ✓

---

## m02 (multi_passage) [ ] checked

**Q:** What sensor data feeds the battery temperature estimate, and how does the Kalman gain weight the prediction?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** kalman · claim 1 → 1 passage(s)

> *US20160079633A1.txt, claim 1:* 1. A method of estimating a temperature of a battery system, the method comprising: receiving battery system temperature measurement data from one or more first temperature sensors associated with the battery system; receiving ambient temperature measurement data associated with an ambient temperature proximate to the battery system from one or more second sensors associated with the battery system; and determining an average estimated temperature of the battery system using, at least in part, an extended Kalman filter based on the battery system temperature measurement data, the ambient temperature measurement data, an energy balance process model associated with the battery system, and a temperature parameter.


**Label:** kalman · "Kalman gain may be calculated" → 2 passage(s)

> *US20160079633A1.txt, summary:* The EKF may operate recursively on new temperature measurements received in a series of measurements and produce a battery system temperature estimate with increased accuracy. In certain embodiments, the EFK may be configured to operate in real time using new input temperature measurements and results derived based on previously received temperature measurements.  [0006] In certain embodiments, the EFK may utilize at least two computational stages: a predication stage and an update stage. In the prediction stage, a battery temperature may be estimated based on a process model and a measurement model. An uncertainty (e.g., a process error covariance) associated with the estimated temperature may also be predicted. The estimated temperature and predicted uncertainty may be passed to the update stage, where measurement uncertainty (e.g., a measurement error covariance) and a Kalman gain may be calculated, and the estimated temperature state measurement may be updated. This information may be provided to the prediction stage for recursive temperature estimation.  [0007] In some embodiments, a method for estimating the temperature of a battery system may include receiving battery system …

> *US20160079633A1.txt, description:* In certain embodiments, the Kalman gain calculated by the Kalman gain calculation module 208 may be an estimate of both the process error covariance and the measurement error covariance.  [0038] In certain embodiments, the Kalman gain may be calculated based on the estimated error from both the prediction stage 200 temperature estimate and the error associated with the measurement model. This may function as a weighting to determine how heavily to weight the predicted temperature from the process model (e.g., implemented using Equation 1) relative to the measurement model (e.g., implemented using Equation 2). The state estimate measurement update module 210 may calculate a predicted temperature based on the Kalman gain, the process model update, and the measurement model estimate.  [0039] After temperature is predicted by the state estimate measurement update module 210, a new measurement error covariance is calculated and provided to the prediction stage 200 which may use it to update the predicted temperature error on a subsequent cycle. The two error covariances (process and measurement) may be passed back and forth between the prediction stage 200 and the update stage 202 and b …


**Key facts:** ambient ✓; Kalman gain ✓

---

## m03 (multi_passage) [ ] checked

**Q:** Which measurements are used to control the electronic expansion valve and to compute the compressor speed command?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** pid_chiller · claim 1 → 1 passage(s)

> *US20230415612A1.txt, claim 1:* 1. A method of managing thermal loads in an electric vehicle, the method comprising: heating, utilizing waste heat from a battery, a battery coolant of a battery coolant loop to form a heated battery coolant; heating a refrigerant of a battery refrigeration loop by exchanging heat with the heated battery coolant; measuring a first refrigerant temperature located at an outlet of a first chiller; measuring a first refrigerant pressure located at the outlet of the first chiller; and controlling a position of a first electronic expansion valve based upon the first refrigerant temperature and the first refrigerant pressure.


**Label:** pid_chiller · claim 7 → 1 passage(s)

> *US20230415612A1.txt, claim 7:* 7. The method of claim 6, further comprising: measuring a first battery coolant temperature located at a battery inlet; and calculating a compressor speed command based upon the coolant flow rate, the first battery coolant temperature, and a battery coolant temperature setpoint.


**Key facts:** refrigerant pressure ✓; compressor speed command ✓

---

## m04 (multi_passage) [ ] checked

**Q:** How does the immersion cooling system control the coolant flow to each battery module, and which sensors support that?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** runners · claim 4 → 1 passage(s)

> *US20250079567A1.txt, claim 4:* 4. The traction battery pack as recited in claim 3, comprising a first flow control valve positioned within the first intake runner, and a second flow control valve positioned within the second intake runner.


**Label:** runners · claim 5 → 1 passage(s)

> *US20250079567A1.txt, claim 5:* 5. The traction battery pack as recited in claim 3, comprising a first temperature sensor positioned within or near the first exhaust runner, and a second temperature sensor positioned within or near the second exhaust runner.


**Label:** runners · abstract → 1 passage(s)

> *US20250079567A1.txt, abstract:* Immersion cooling systems are provided for traction battery packs. An exemplary immersion cooling system may include an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and a first interior volume of a compartmentalized battery module, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume. A cooling fluid (e.g., a dielectric) may be selectively communicated through the first interior volume for thermally managing the battery module. A flow control valve may be positioned within the first intake runner for controlling the flow through the first interior volume, and a control module may control a position of the valve based at least on a temperature of the cooling fluid exiting the first interior volume.


**Key facts:** flow control valve ✓; temperature sensor ✓

---

## m05 (multi_passage) [ ] checked

**Q:** Why does the off-board charging system care about the coolant volume next to the battery pack, and what limits how fast coolant can flow?

Expected intent `document_qa`, tools `['search_uploaded_documents']`  

**Label:** offboard · "absorbs the heat produced by the battery pack" → 1 passage(s)

> *US20170297431A1.txt, description:* All of the values in the denominator represent various coefficients and thicknesses of the tubing materials. These values depend on the different thermal layers between the battery cells and the cooling system and may be different for each type of vehicle.  [0000] q . = A  ( T cell - T coolant ) ( 1 h + L k c + 1 h c + t k s + t   2 k s )  [0035] Step 407 involves a calculation of the total coolant volume in the tubes adjacent to the battery pack. This specific volume is important because it represents the volume of coolant which absorbs the heat produced by the battery pack during the charging process.  [0036] This volume may be used to determine the temperature gradient 408 between the coolant tube inlet and outlet in each battery pack module. Maximizing the flow rate through the cooling tubes may minimize this temperature gradient. A sample calculation of how to determine this temperature gradient is provided, where the values on the left hand side are obtained from either database or prior calculations. This particular calculation shows the estimated coolant temperature gradient when using a 300 kW charger.  [0000] q mc p = Δ   T = 3.28  K  [0037] The final calculation 40 …


**Label:** offboard · "maximum pressure which the pipes" → 1 passage(s)

> *US20170297431A1.txt, description:* The following is a sample calculation based on multiple parameters obtained from the database which determines the maximum flow velocity based on a given pump power.  [0000] W . h = ηρ   q .  gh l = ρ   qgf  L D  V 2 2  g = ηρ   V ( 0.00012   m 2 1 )  g  24  μ ρ   VD  L D  V 2 2  g = η   V ( 0.00012   m 2 1 )  12  μ D  L D  V  [0029] Now solving for velocity V:  [0000] V 2 = W . h  D 2 12  ημ   L  ( 0.00012   m 2 1 ) = 18.56   m 2 s 2  [0030] Using the values from above, as well as the pump efficiency η, solve for Vmax For now, assume the pump is 100% efficient.  [0000] V max=4.308 m/s  [0031] An alternative limiting factor in step 403 may be the maximum pressure which the pipes of the on-board cooling system can handle. In the case of the Tesla Model S for example, the pipes are made of some kind of metal, including but not limited to copper or aluminum, and are 0.5 mm thick. Using the flow velocity calculated above in step 403, the pressure within the tubing system can be determined.


**Key facts:** pressure ✓

---

## c01 (claim_explanation) [ ] checked

**Q:** Where is the sensing coil located according to claim 2?

Selected documents: US11316383B1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** sensing_coil · claim 2 → 1 passage(s)

> *US11316383B1.txt, claim 2:* 2. The wireless power transmitting device of claim 1 wherein the wireless power transmitting coil has an interior region and wherein the sensing coil is located in the interior region.


**Key facts:** interior region ✓

---

## c02 (claim_explanation) [ ] checked

**Q:** What does claim 4 add to the control circuitry?

Selected documents: US11316383B1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** sensing_coil · claim 4 → 1 passage(s)

> *US11316383B1.txt, claim 4:* 4. The wireless power transmitting device of claim 1 wherein the control circuitry comprises a subtractor and wherein the control circuitry is configured to subtract interference received from the additional wireless power transmitting device using the sensing coil from a signal received from the wireless power transmitting coil during foreign object detection operations.


**Key facts:** subtract ✓

---

## c03 (claim_explanation) [ ] checked

**Q:** Under claim 3, what happens when the probability value is below the threshold?

Selected documents: US20190074730A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** ml_fod · claim 3 → 1 passage(s)

> *US20190074730A1.txt, claim 3:* 3. The wireless power transmitting device of claim 1, wherein the control circuitry is further configured to: in accordance with determining that the probability value is less than the threshold, cause an alert, wherein the alert comprises an alert selected from the group consisting of: a visual alert and an auditory alert.


**Key facts:** alert ✓

---

## c04 (claim_explanation) [ ] checked

**Q:** Which additional component does claim 8 add to the immersion cooling system?

Selected documents: US20250079567A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** runners · claim 8 → 1 passage(s)

> *US20250079567A1.txt, claim 8:* 8. The traction battery pack as recited in claim 1, wherein the immersion cooling system further includes a reservoir that is fluidly connected to the intake manifold.


**Key facts:** reservoir ✓

---

## c05 (claim_explanation) [ ] checked

**Q:** What are the dividers made of according to claim 3?

Selected documents: US20230369708A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** grouped · claim 3 → 1 passage(s)

> *US20230369708A1.txt, claim 3:* 3. The immersion cooling system of claim 1, wherein each of the plurality of dividers includes: a first metal plate; an insulating member; and a second metal plate.


**Key facts:** metal plate ✓; insulating member ✓

---

## c06 (claim_explanation) [ ] checked

**Q:** Which temperature does claim 3 use as the temperature parameter?

Selected documents: US20160079633A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** kalman · claim 3 → 1 passage(s)

> *US20160079633A1.txt, claim 3:* 3. The method of claim 2, wherein the temperature parameter associated with the cooling system comprises an inlet coolant temperature of the battery system.


**Key facts:** inlet coolant temperature ✓

---

## c07 (claim_explanation) [ ] checked

**Q:** According to claim 7, where can the fluid collection manifold draw immersion fluid from?

Selected documents: US12563707B2.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** electronics · claim 7 → 1 passage(s)

> *US12563707B2.txt, claim 7:* 7. The cooling module of claim 1, wherein the fluid collection manifold is configured to draw immersion fluid from the outlet of another cooling module constructed according to claim 1.


**Key facts:** another cooling module ✓

---

## c08 (claim_explanation) [ ] checked

**Q:** What does claim 2 specify about the pumps?

Selected documents: US20170297431A1.txt  
Expected intent `document_qa`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** offboard · claim 2 → 1 passage(s)

> *US20170297431A1.txt, claim 2:* 2. The method as recited in claim 1 wherein a first pump off-board the electric vehicle having a first pumping capacity provides the coolant at the first rate during the recharging of the electric battery and a second pump in the coolant loop on-board the electric vehicle having a second pumping capacity at the second rate after the recharging of the electric battery, the first pumping capacity being greater than the second pumping capacity.


**Key facts:** second pump ✓

---

## n01 (patent_lookup) [ ] checked

**Q:** What type of pump does claim 2 of US12563707B2 specify?

Expected intent `patent_lookup`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** electronics · claim 2 → 1 passage(s)

> *US12563707B2.txt, claim 2:* 2. The cooling module of claim 1, wherein the pump is a positive displacement pump.


**Key facts:** positive displacement ✓

---

## n02 (patent_lookup) [ ] checked

**Q:** What problem does US20230369708A1 address?

Expected intent `patent_lookup`, tools `['retrieve_evidence']`  

**Label:** grouped · abstract → 3 passage(s)

> *US20230369708A1.txt, abstract:* An immersion cooling system for a battery system includes a battery enclosure and G battery cell groups arranged in the battery enclosure. Each of the G battery cell groups include C battery cells, where G and C are integers greater than one. A plurality of dividers are arranged between each of the G battery cell groups. A gas manifold removes vent gases from each of the G battery cell groups.  INTRODUCTION  [0001] The information provided in this section is for the purpose of generally presenting the context of the disclosure. Work of the presently named inventors, to the extent it is described in this section, as well as aspects of the description that may not otherwise qualify as prior art at the time of filing, are neither expressly nor impliedly admitted as prior art against the present disclosure.  [0002] The present disclosure relates to battery systems, and more particularly to immersion cooling systems for battery systems of electric vehicles.  [0003] Electric vehicles (EVs) such as battery electric vehicles (BEV), fuel cell vehicles or hybrid vehicles include a battery system with one or more battery cells, modules and/or packs. A power control system controls charging an …

> *US20230369708A1.txt, abstract:* During driving, one or more electric motors of the EV receive power from the battery system to provide propulsion for the vehicle and/or to return power to the battery system during regeneration and/or charging from a utility.  [0004] During operation, power is delivered by the battery system to the motor(s) and returned by the motor(s) to the battery system using one or more components such as power inverters, DC-DC converters and/or other components. The battery system is designed to deliver high power when requested, absorb high power quickly during charging from the utility and/or to absorb high power during regeneration.  [0005] The battery systems are expected to continue to increase in power density and operate at higher voltage levels. When operating under these conditions, significant heating of the battery cells, the battery modules, the battery pack, the power inverters, the DC-DC converters and/or other EV components can occur.


**Label:** grouped · "prevent thermal runaway propagation" → 1 passage(s)

> *US20230369708A1.txt, description:* As a battery cell begins to fail, hot gas/particles are emitted by the battery cell. The hot gas/particles from the failed battery cell can cause heat transfer to other adjacent battery cells. As the adjacent battery cells are heated, they too can fail and cause further failures or propagation.  [0029] An immersion cooling system according to the present disclosure prevents hot gas from heating neighboring battery cells by separating the battery cells into battery cell groups, supplying dielectric fluid to the battery cell groups, and managing vent gas generated by each of the battery cell groups to prevent the vent gas from that battery cell group from causing further battery cell failures due to overheating. In other words, the immersion cooling system prevents hot gas convection to neighboring battery cells to prevent thermal runaway propagation. As will be described further below, the immersion cooling system utilizes edge cooling or both edge and face cooling to prevent thermal runaway propagation to neighboring battery cells.  [0030] The immersion cooling system according to the present disclosure has improved cooling performance that enables DC fast charging while protecting …


**Key facts:** thermal runaway ✓

---

## n03 (patent_lookup) [ ] checked

**Q:** Summarize claim 1 of US20090249807A1.

Expected intent `patent_lookup`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** hvac_chiller · claim 1 → 1 passage(s)

> *US20090249807A1.txt, claim 1:* 1. A HVAC and battery thermal system for a vehicle having a passenger cabin and a battery pack, the system comprising: a refrigerant loop including a compressor, a condenser, a first leg and a second leg, the first leg including an evaporator expansion device and an evaporator configured to provide cooling to the passenger cabin, and the second leg including a battery expansion device and a chiller; and a coolant loop configured to direct a coolant through the battery pack and including a controllable coolant routing valve, a bypass branch and a chiller branch, the chiller being located in the chiller branch, and the coolant routing valve having a bypass outlet that directs the coolant into the bypass branch and a chiller outlet that directs the coolant into the chiller branch and through the chiller.


**Key facts:** chiller ✓; coolant routing valve ✓

---

## n04 (patent_lookup) [ ] checked

**Q:** What does claim 1 of US20190315232A1 require the processor to estimate?

Expected intent `patent_lookup`, tools `['retrieve_document_section', 'retrieve_evidence']`  

**Label:** predictive · claim 1 → 1 passage(s)

> *US20190315232A1.txt, claim 1:* 1. A system comprising: a processor; and a memory coupled to the processor and comprising computer-readable program code that when executed by the processor causes the processor to perform operations comprising: determining a current temperature of a battery of a vehicle; and determining if the current temperature of the battery is within a threshold temperature range of the battery, wherein if the processor determines that the current temperature of the battery is within a threshold temperature range of the battery, the processor performs operations comprising: determining an estimated temperature at arrival of the battery; and determining if the estimated temperature at arrival of the battery is within the threshold temperature range of the battery, wherein if the processor determines the estimated temperature at arrival of the battery exceeds a maximum or is less than a minimum temperature of the battery, the processor performs an operation of initiating a thermal management process.


**Key facts:** estimated temperature at arrival ✓

---

## x01 (comparison) [ ] checked

**Q:** Compare how these two patents use additional coils besides the power transmitting coil.

Selected documents: US11316383B1.txt, US9178361B2.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** sensing_coil · claim 1 → 1 passage(s)

> *US11316383B1.txt, claim 1:* 1. A wireless power transmitting device for transmitting wireless power to a wireless power receiving device in the presence of an additional wireless power transmitting device, comprising: wireless power transmitting circuitry having a wireless power transmitting coil configured to transmit wireless power signals to the wireless power receiving device; a sensing coil; and control circuitry configured to detect foreign objects using the wireless power transmitting coil while using the sensing coil to reduce interference from the additional wireless power transmitting device.


**Label:** fod_coils · claim 1 → 1 passage(s)

> *US9178361B2.txt, claim 1:* 1. A wireless power charging system for charging a separate device having a power receiver coil, the wireless power charging system comprising: at least one power transmitter coil configured for transmitting power by inductive coupling to the power receiver coil in the separate device, the power transmitter coil characterized by a transmitter coil dimension that is a lateral dimension of the power transmitter coil; at least one foreign object detection (FOD) coil located proximate to the power transmitter coil and oriented to detect foreign objects that disturb the power transmission, the FOD coil characterized by a FOD coil dimension that is a lateral dimension of the FOD coil and that is smaller than the lateral dimension of the power transmitter coil, wherein the at least one FOD coil comprises two or more FOD coils, the at least one power transmitter coil comprises two or more power transmitter coils; and a controller configured to select power transmitter coils for activation based on which FOD coils have detected foreign objects.


---

## x02 (comparison) [ ] checked

**Q:** Compare where the battery cooling comes from in these two documents.

Selected documents: US20170297431A1.txt, US20090249807A1.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** offboard · abstract → 1 passage(s)

> *US20170297431A1.txt, abstract:* A method of providing coolant to an electric battery for powering a drive train of an electric vehicle is provided. The method includes providing coolant from a coolant source off-board the electric vehicle at a first rate to cool the electric battery during recharging of the electric battery; and circulating coolant through a coolant loop on-board the electric vehicle at a second rate less than the first rate to cool the electric battery after the recharging of the electric battery.  [0001] The present disclosure relates generally to temperature management of electric vehicle batteries and more specifically to off-board temperature management of electric vehicle batteries during charging.


**Label:** hvac_chiller · abstract → 1 passage(s)

> *US20090249807A1.txt, abstract:* A HVAC and battery thermal system and method for a vehicle having a passenger cabin and a battery pack is disclosed. The system may comprise a refrigerant loop and a coolant loop. The refrigerant loop includes a first leg and a second leg, the first leg including an expansion device and an evaporator, and the second leg including an expansion device and a chiller. The coolant loop directs coolant through the battery pack and includes a controllable coolant routing valve, a bypass branch and a chiller branch, with the chiller in the chiller branch. The coolant routing valve has a bypass outlet that directs the coolant into the bypass branch and a chiller outlet that directs the coolant into the chiller branch. The coolant loop may also include a radiator branch and battery radiator, with the coolant routing valve including a radiator outlet that directs the coolant into the radiator branch.


---

## x03 (comparison) [ ] checked

**Q:** What are the technical differences between these two immersion-cooled battery designs?

Selected documents: US20230369708A1.txt, US8852772B2.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** grouped · claim 1 → 1 passage(s)

> *US20230369708A1.txt, claim 1:* 1. An immersion cooling system for a battery system, comprising: a battery enclosure; G battery cell groups arranged in the battery enclosure, wherein each of the G battery cell groups include C battery cells, where G and C are integers greater than one; a plurality of dividers arranged between each of the G battery cell groups; and a gas manifold configured to receive vent gases from each of the G battery cell groups.


**Label:** sealed · claim 1 → 1 passage(s)

> *US8852772B2.txt, claim 1:* 1. A vehicle battery pack with a self-contained liquid cooling system comprising: a sealed container having an interior space; a battery assembly disposed within the interior space of the container, the battery assembly including a plurality of battery cells having at least one fluid channel formed therebetween; a dielectric fluid disposed within the at least one fluid channel in contact with the battery cells of the battery assembly and configured to heat and cool the battery assembly; a heating element disposed within the interior space configured to heat the dielectric fluid; and a cooling element disposed within the interior space configured to cool the dielectric fluid.


---

## x04 (comparison) [ ] checked

**Q:** Compare how these two documents use the resonance of the coil to detect foreign objects.

Selected documents: US11646607B2.txt, US10804750B2.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** peak_freq · abstract → 1 passage(s)

> *US11646607B2.txt, abstract:* A wireless power receiver including a transmitter configured to transmit to a wireless power transmitter, a foreign object detection status packet including a mode bit field indicating whether a foreign object detection status packet includes a reference peak frequency of the wireless power receiver, in which the reference peak frequency is pre-assigned to the wireless power receiver; and a receiver configured to receive from the wireless power transmitter, a response indicating the foreign object is present or not present in a charging area of the wireless power transmitter, wherein the response is determined based on a comparison of a measured peak frequency of a power signal transmitted by the wireless power transmitter and an adaptable threshold frequency adapted based on the reference peak frequency included in the foreign object detection status packet from the wireless power receiver.  CROSS-REFERENCE TO RELATED APPLICATIONS  [0001] This Application is a Continuation of U.S. patent application Ser. No. 16/314,559 filed on Dec. 31, 2018 (now U.S. Pat. No. 11,070,095 issued on Jul. 20, 2021), which is the National Phase of PCT International Application No. PCT/KR2017/006975 fi …


**Label:** qfactor · abstract → 2 passage(s)

> *US10804750B2.txt, abstract:* A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor from monitoring the voltage.  RELATED DOCUMENTS  [0001] This application claims priority to U.S. Provisional Patent Application 62/546,988, filed on Aug. 17, 2017, which is herein incorporated by reference in its entirety.

> *US10804750B2.txt, summary:* [0006] In accordance with some embodiments of the present invention, a wireless power transmitter that measures the Q-factor is provided. In accordance with some embodiments, the wireless power transmitter includes a transmit coil; a capacitor coupled in series with the transmit coil to form a resonant circuit; a bridge circuit coupled to the resonant circuit; a control circuit coupled to control the bridge circuit to provide voltages across the resonant circuit; a charging circuit coupled to charge the capacitor with a charging voltage and coupled to be controlled by the control circuit; and a detection circuit coupled to receive a voltage across the capacitor and provide data related to the voltage to the control circuit while the resonant circuit.  [0007] A method of measuring a Q-factor in a wireless power transmitter includes charging a capacitor in a LC tank circuit that includes a transmission coil to a voltage; starting a Q-factor determining by coupling the LC tank circuit to ground to form a free-oscillating circuit; monitoring the voltage across the capacitor as a function of time as the LC tank circuit oscillates; and determining the resonant frequency and the Q-factor  …


---

## x05 (comparison) [ ] checked

**Q:** Contrast how these two patents circulate the immersion fluid.

Selected documents: US12563707B2.txt, US20250079567A1.txt  
Expected intent `compare`, tools `['compare_patents']`  

**Label:** electronics · abstract → 1 passage(s)

> *US12563707B2.txt, abstract:* Embodiments of the present invention provide a cooling module for cooling heat-generating electronic devices in an immersion cooling system. The cooling module includes an integrated pump, which draws immersion fluid from the surrounding dielectric bath and drives it into a pressurized plenum to pressurize the coolant fluid and drive the pressurized coolant fluid through a nozzle plate containing a microconvective nozzle array. The array accelerates the fluid to produce a multiplicity of microjets that impinge on a surface of the heat-generating electronic device to be cooled. The effluent from the cooling module may be directed to flow into and wash over nearby heat-generating devices to help cool the nearby heat-generating devices. The effluent may also be directed to the inlets of daughter cooling modules attached to other heat-generating electronic devices. In some embodiments, cooling modules of the present invention may include fluid collection and fluid discharge manifolds that may be configured and arranged to target specific regions of an immersion bath that might otherwise become relatively stagnant, thereby enhancing overall system circulation and convective environment  …


**Label:** runners · abstract → 1 passage(s)

> *US20250079567A1.txt, abstract:* Immersion cooling systems are provided for traction battery packs. An exemplary immersion cooling system may include an intake manifold, an exhaust manifold, a first intake runner fluidly connected to the intake manifold and a first interior volume of a compartmentalized battery module, and a first exhaust runner fluidly connected to the exhaust manifold and the first interior volume. A cooling fluid (e.g., a dielectric) may be selectively communicated through the first interior volume for thermally managing the battery module. A flow control valve may be positioned within the first intake runner for controlling the flow through the first interior volume, and a control module may control a position of the valve based at least on a temperature of the cooling fluid exiting the first interior volume.


---

## u01 (unanswerable) [ ] checked

**Q:** What is the warranty period of the immersion-cooled traction battery pack with intake runners?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* Hard negative - the Kalman patent mentions warranty costs in general.

---

## u02 (unanswerable) [ ] checked

**Q:** How much does it cost to manufacture the charging pad with small detection coils?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u03 (unanswerable) [ ] checked

**Q:** In which countries is the Q-factor detection transmitter sold?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## u04 (unanswerable) [ ] checked

**Q:** Which neural network does the Kalman filter battery patent train on cell temperatures?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* False premise - the patent uses an extended Kalman filter, no neural network.

---

## u05 (unanswerable) [ ] checked

**Q:** What is the best stock to buy this year?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

*Notes:* Off-topic.

---

## u06 (unanswerable) [ ] checked

**Q:** What is the maximum operating altitude of the off-board rapid charging station?

Expected: **abstain** (not answerable from the corpus)  
Expected intent `document_qa`, tools `['search_uploaded_documents']`  

---

## l01 (legal) [ ] checked

**Q:** Would selling a charger based on the machine-learning patent infringe the sensing-coil patent?

Selected documents: US20190074730A1.txt, US11316383B1.txt  
Expected intent `compare`, tools `['compare_patents']`, legal flag True  

**Label:** ml_fod · claim 1 → 1 passage(s)

> *US20190074730A1.txt, claim 1:* 1. A wireless power transmitting device with a charging surface configured to receive a wireless power receiving device that has a wireless power receiving coil, the wireless power transmitting device comprising: a plurality of coils; wireless power transmitting circuitry coupled to the plurality of coils and configured to transmit wireless power signals with the plurality of coils; and control circuitry configured to: gather measurements from one or more coils of the plurality of coils; determine, using the measurements, a probability value indicative of whether a wireless power receiving device that has a wireless power receiving coil is present on the charging surface; and in accordance with determining that the probability value exceeds a threshold, cause the wireless power transmitting circuitry to transmit wireless power signals with one or more coils of the plurality of coils.


**Label:** sensing_coil · claim 1 → 1 passage(s)

> *US11316383B1.txt, claim 1:* 1. A wireless power transmitting device for transmitting wireless power to a wireless power receiving device in the presence of an additional wireless power transmitting device, comprising: wireless power transmitting circuitry having a wireless power transmitting coil configured to transmit wireless power signals to the wireless power receiving device; a sensing coil; and control circuitry configured to detect foreign objects using the wireless power transmitting coil while using the sensing coil to reduce interference from the additional wireless power transmitting device.


---

## l02 (legal) [ ] checked

**Q:** Is US8852772B2 still valid and enforceable today?

Expected intent `patent_lookup`, tools `['retrieve_evidence']`, legal flag True  

**Label:** sealed · abstract → 1 passage(s)

> *US8852772B2.txt, abstract:* A Lithium Ion battery cooling system for use in a hybrid vehicle comprises a plurality of self-contained liquid cooling modules, each cooling module including a closed and sealed container having an interior space. Each cooling module includes a battery assembly disposed within the interior space of the container and a plurality of battery cells having at least one fluid channel formed therebetween for receiving a fluid therein. A dielectric fluid is disposed within the at least one fluid channel. The dielectric fluid substantially immerses and is in contact with the battery assembly to heat and cool the battery assembly. A heating element is disposed within the interior space and heats the dielectric fluid. A cooling element is disposed within the interior space and cools the dielectric fluid.


---

## l03 (legal) [ ] checked

**Q:** Can I copy the thermal management systems in these two patents without infringing them?

Selected documents: US20230415612A1.txt, US11214114B2.txt  
Expected intent `compare`, tools `['compare_patents']`, legal flag True  

**Label:** pid_chiller · claim 1 → 1 passage(s)

> *US20230415612A1.txt, claim 1:* 1. A method of managing thermal loads in an electric vehicle, the method comprising: heating, utilizing waste heat from a battery, a battery coolant of a battery coolant loop to form a heated battery coolant; heating a refrigerant of a battery refrigeration loop by exchanging heat with the heated battery coolant; measuring a first refrigerant temperature located at an outlet of a first chiller; measuring a first refrigerant pressure located at the outlet of the first chiller; and controlling a position of a first electronic expansion valve based upon the first refrigerant temperature and the first refrigerant pressure.


**Label:** parallel_loops · claim 1 → 1 passage(s)

> *US11214114B2.txt, claim 1:* 1. A thermal management system for a vehicle comprising: a traction battery for propelling the vehicle; a motor coupled to the traction battery; a first cooling loop circulating fluid to cool the traction battery; and a second cooling loop circulating fluid to cool the traction motor; a third loop for regulating a passenger cabin temperature and selectively coupled to the first and second cooling loops; and a radiator selectively in communication with the first cooling loop and second cooling loop, wherein the first loop, the second loop are in fluid communication and arranged in parallel to be cooled by the radiator, a radiator valve for selectively controlling fluid flow through the radiator, wherein in a first position fluid flows through the radiator and in a second position fluid bypasses the radiator, a battery valve for selectively controlling fluid flow through the traction battery, wherein when the radiator valve is in a first position, fluid flows through the radiator and when the battery valve is in a first position fluid flows in parallel through the first loop and the second loop, the radiator thereby cooling the battery and the traction motor in parallel.


---
