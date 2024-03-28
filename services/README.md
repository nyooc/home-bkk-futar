# Services

`home-bkk-futar.service` is a template unit file to run home-bkk-futar right on startup as a 
service. This way the matrix display will work right after you boot your Pi.

First, customize this unit file by thoroughly checking all entries. The main settings are the 
following:
- `WorkingDirectory=` Set your path to the project root here.
- `ExecStart=` You can set either the `main` (infinite operation) or the `button` (button-actuated 
  operation) entrypoint here.
- `StandardOutput=` The place to send the logs is currently set to `journalctl`. You have some other
  options, too.
- `Restart=` On a failure we currently don't restart the service.

When ready, copy this file to `/etc/systemd/system/`. Reload the unit files, enable and start the 
service:

```shell
sudo systemctl daemon-reload
sudo systemctl enable home-bkk-futar.service
sudo systemctl start home-bkk-futar.service
```
