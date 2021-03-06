 IM - Infrastructure Manager
============================

* Version ![PyPI](https://img.shields.io/pypi/v/im.svg)
* PyPI ![PypI](https://img.shields.io/pypi/dm/IM.svg)

IM is a tool that deploys complex and customized virtual infrastructures on IaaS
Cloud deployments (such as AWS, OpenStack, etc.). It eases the access and the
usability of IaaS clouds by automating the VMI (Virtual Machine Image)
selection, deployment, configuration, software installation, monitoring and
update of the virtual infrastructure. It supports APIs from a large number of virtual
platforms, making user applications cloud-agnostic. In addition it integrates a
contextualization system to enable the installation and configuration of all the
user required applications providing the user with a fully functional
infrastructure.

Read the documentation and more at http://www.grycap.upv.es/im.

There is also an Infrastructure Manager YouTube reproduction list with a set of videos with demos
of the functionality of the platform: https://www.youtube.com/playlist?list=PLgPH186Qwh_37AMhEruhVKZSfoYpHkrUp.


1. INSTALLATION
===============

1.1 REQUISITES
--------------

IM is based on Python, so Python 2.6 or higher runtime and standard library must
be installed in the system.

If you use pip to install the IM, all the requisites will be installed.
However, if you install IM from sources you should install:

 + The RADL parser (https://github.com/grycap/radl), available in pip
   as the 'RADL' package.

 + The paramiko ssh2 protocol library for python version 1.14 or later
(http://www.lag.net/paramiko/), typically available as the 'python-paramiko' package.

 + The YAML library for Python, typically available as the 'python-yaml' or 'PyYAML' package.

 + The SOAPpy library for Python, typically available as the 'python-soappy' or 'SOAPpy' package.
 
 + The Netaddr library for Python, typically available as the 'python-netaddr' package.
 
 + The boto library version 2.29 or later
   must be installed (http://boto.readthedocs.org/en/latest/).

 + The apache-libcloud library version 0.18 or later
   must be installed (http://libcloud.apache.org/).

 + Ansible (http://www.ansibleworks.com/) to configure nodes in the infrastructures.
   In particular, Ansible 1.4.2+ must be installed. The current recommended version is 1.9.4 untill the 2.X versions become stable.
   To ensure the functionality the following values must be set in the ansible.cfg file (usually found in /etc/ansible/):

```
[defaults]
transport  = smart
host_key_checking = False
# For old versions 1.X
sudo_user = root
sudo_exe = sudo

# For new versions 2.X
become_user      = root
become_method    = sudo

[paramiko_connection]

record_host_keys=False

[ssh_connection]

# Only in systems with OpenSSH support to ControlPersist
ssh_args = -o ControlMaster=auto -o ControlPersist=900s
# In systems with older versions of OpenSSH (RHEL 6, CentOS 6, SLES 10 or SLES 11) 
#ssh_args =
pipelining = True
```

1.2 OPTIONAL PACKAGES
---------------------

In case of using the SSL secured version of the XMLRPC API the SpringPython
framework (http://springpython.webfactional.com/) must be installed.

In case of using the REST API the Bottle framework
(http://bottlepy.org/) must be installed.

In case of using the SSL secured version of the REST API the CherryPy Web
framework (http://www.cherrypy.org/) and pyOpenSSL must be installed.

1.3 INSTALLING
--------------

### 1.3.1 FROM PIP

**WARNING: The SOAPpy distributed with pip does not work correctly so you must install
the packages 'python-soappy' or 'SOAPp'y before installing the IM with pip.**

**WARNING: In some GNU/Linux distributions (RHEL 6 or equivalents) you must uninstall
the packages 'python-paramiko' and 'python-crypto' before installing the IM with pip.**

You only have to install the IM package through the pip tool.

```
pip install IM
```

Pip will install all the pre-requisites needed. So Ansible  1.4.2 or later will
 be installed in the system. Yo will also need to install the sshpass command
 ('sshpass' package in main distributions). In some cases it will need to have installed 
 the GCC compiler and the python developer libraries ('python-dev' or 'python-devel'
 packages in main distributions).

You must also remember to modify the ansible.cfg file setting as specified in the
REQUISITES section.

### 1.3.2 FROM SOURCE

Select a proper path where the IM service will be installed (i.e. /usr/local/im,
/opt/im or other). This path will be called IM_PATH

```
$ tar xvzf IM-X.XX.tar.gz
$ chown -R root:root IM-X.XX
$ mv IM-X.XX /usr/local
```

Finally you must copy (or link) $IM_PATH/scripts/im file to /etc/init.d directory.

```
$ ln -s /usr/local/im/scripts/im /etc/init.d/im
```

1.4 CONFIGURATION
-----------------

In case that you want the IM service to be started at boot time, you must
execute the next set of commands:

On Debian Systems:

```
$ chkconfig im on
```

Or for newer systems like ubuntu 14.04:

```
$ sysv-rc-conf im on
```

On RedHat Systems:

```
$ update-rc.d im start 99 2 3 4 5 . stop 05 0 1 6 .
```

Or you can do it manually:

```
$ ln -s /etc/init.d/im /etc/rc2.d/S99im
$ ln -s /etc/init.d/im /etc/rc3.d/S99im
$ ln -s /etc/init.d/im /etc/rc5.d/S99im
$ ln -s /etc/init.d/im /etc/rc1.d/K05im
$ ln -s /etc/init.d/im /etc/rc6.d/K05im
```

Adjust the installation path by setting the IMDAEMON variable at /etc/init.d/im
to the path where the IM im_service.py file is installed (e.g. /usr/local/im/im_service.py),
or set the name of the script file (im_service.py) if the file is in the PATH
(pip puts the im_service.py file in the PATH as default).

Check the parameters in $IM_PATH/etc/im.cfg or /etc/im/im.cfg. Please pay attention
to the next configuration variables, as they are the most important

DATA_FILE - must be set to the full path where the IM data file will be created
         (e.g. /usr/local/im/inf.dat). Be careful if you have two different instances
         of the IM service running in the same machine!!.

CONTEXTUALIZATION_DIR - must be set to the full path where the IM contextualization files
		are located. In case of using pip installation the default value is correct
		(/usr/share/im/contextualization) in case of installing from sources set to
		$IM_PATH/contextualization (e.g. /usr/local/im/contextualization)

### 1.4.1 SECURITY

Security is disabled by default. Please notice that someone with local network access can "sniff" the traffic and
get the messages with the IM with the authorisation data with the cloud providers.

Security can be activated both in the XMLRPC and REST APIs. Setting this variables:

XMLRCP_SSL = True

or

REST_SSL = True

And then set the variables: XMLRCP_SSL_* or REST_SSL_* to your certificates paths.

2. DOCKER IMAGE
===============

A Docker image named `grycap/im` has been created to make easier the deployment of an IM service using the 
default configuration. Information about this image can be found here: https://registry.hub.docker.com/u/grycap/im/.

How to launch the IM service using docker:

```sh
sudo docker run -d -p 8899:8899 -p 8800:8800 --name im grycap/im 
```
