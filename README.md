# PlanIt
PlanIt is a tool designed for point-to-point link quality simulation and regional IoT network planning. It uses [Splat!](http://www.qsl.net/kd2bd/splat.html). It includes two sets of tools for you to plan your IoT network:

* A web based tool for small scale point-to-point visualization in Google Map
* A CLI tool to compute overall link quality.

### Install
* You need to set up functional Splat! and add splat to your environmental path. See documentation [here](http://www.qsl.net/kd2bd/splat.pdf).
* Install the Python library through ```requirement.txt```.
* This repo comes with sqlite3 database. If you need to create your own database, please check out ```kml.py```.


### Usage
* For web tool, simply run the ```app.py```. By default it runs on port ```8887```. I will add more CLI arguments in the future.
* For CLI tool, currently the ratio is hardcoded. You need to change the ratio manually.


### Additional Notes
Since PlanIt uses Splat!, it will create thousands config files in workspace for Splat! to read the inputs. Splat! will also create tons of reports in the current working folder. ``run.sh``` is created for switching virtualenv and cleaning out the report files.