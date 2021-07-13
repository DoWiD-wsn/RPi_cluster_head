# RPi-based Cluster Head

The Raspberry Pi-based cluster head is a gateway used in our wireless sensor network testbed.
The cluster head software is basically a Python script the takes over ZigBee packets from the sensor network (received by an Xbee 3 module), processes the information and stores them in a remote MySQL database.


## Contents

```
.
└── source              : Python sources
```


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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
