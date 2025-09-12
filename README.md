<h1 align="center">vmpheus</h1>

<h3> he be managing and shi fr fr </h3>

---
<h4> About:</h4>
vmpheus was a bot created for hackclub summer of making to help in the project review process, vmpheus is a collaborated project between me and Eric built over the span of 5 days.

---
<h4> but i know damn well noone cares about that so here's the good stuff

<h3>features:</h3>

* Web dashboard for ease of management
* Incredibly scalable API 
* Azure integration
* Ease of use with alot of management features
---

<h4> Slack bot commands: </h4>

* `/sr` for admin commands
* `/sos` for staff support
* `/utils` to request a utils api key
* `/vm` for vm control
<br>
<h5>These commands were made with ease of management and usability in mind!

---

<h4> How to run..? </h4>

<h5> API: </h5>

You're first going to want to run it once via the bash script ```setup.sh``` with an open port
```angular2html
bash setup.sh *port*
```
afterwards you should edit the config file with all your API keys :)
```angular2html
nano config.json
```
then run the bash script again
```angular2html
bash setup.sh *port*
```
if you plan to host this on a domain that depends on the platfrom so lookup a tutorial :))

<h5> Bot </h5>

First run it once to initialize files!

```angular2html
python main.py
```

then proceed to configure ``auth.json`` with your api key and domain/local host

```angular2html
nano auth.json
```
then finally run the app

```angular2html
python main.py &
```