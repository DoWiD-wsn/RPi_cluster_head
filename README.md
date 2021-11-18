# RPi-based Cluster Head

The Raspberry Pi-based cluster head is a gateway used in our wireless sensor network testbed.
The cluster head software is basically a Python script the takes over ZigBee packets from the sensor network (WSN), received by an Xbee 3 module, processes the information and stores them in a remote MySQL database.

The cluster head used in our WSN is based on a Raspberry Pi 3 model B (shortly called RPi) equipped with a 32 GB microSD card running a recent version of [Raspberry Pi OS](https://www.raspberrypi.org/software/) (previously called Raspbian) and a Digi Xbee 3 radio transceiver connected via an [Waveshare Xbee USB adapter](https://www.waveshare.com/xbee-usb-adapter.htm).
However, the scripts also work on any other system running a Debian/Ubuntu OS and having the Xbee connected via a serial interface.


## Contents

```
.
└── source              : Python sources
```

The setup and prerequisites for the Python script running on the cluster head are described in [source/setup.md](source/setup.md).


## Built with

* [Python 3.7.3](https://www.python.org/downloads/release/python-373/) - cluster head software


## Contributors

* **Dominik Widhalm** - [***DC-RES***](https://informatics.tuwien.ac.at/doctoral/resilient-embedded-systems/) - [*UAS Technikum Wien*](https://embsys.technikum-wien.at/staff/widhalm/)

Contributions of any kind to improve the project are highly welcome.
For coding bugs or minor improvements simply use pull requests.
However, for major changes or general discussions please contact [Dominik Widhalm](mailto:widhalm@technikum-wien.at?subject=ASN(x)%20on%20GitHub).


## Changelog

A list of prior versions and changes between the updates can be found inn the [CHANGELOG.md](CHANGELOG.md) file.


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
