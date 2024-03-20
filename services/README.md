# Services

`home-bkk-futar.service` is a template unit file to run home-bkk-futar right on startup as a 
service. This way the matrix display will work right after you boot your Pi.

First, customize this unit file as least by rewriting the `WorkingDirectory=` setting. Thoroughly 
check all other entries. How do you want to read your logs? (Current setting is via `journalctl`.)
Do you want to restart the service on a failure? (Currently, no.)

When ready, copy this file to `/etc/systemd/system/`. Reload the unit files, enable and start the 
service:

```shell
sudo systemctl daemon-reload
sudo systemctl enable home-bkk-futar.service
sudo systemctl start home-bkk-futar.service
```
