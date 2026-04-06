# TraCI examples

## Prerequisites
- **Python**: Ensure Python 3.x is installed on your computer
- **Note**: On new **Linux** systems, the command is `python3`, not `python`
- **Dependencies**: None. This script uses only Python's built-in tools

## pt_priority.py - basic usage
1. Save the script on your computer
2. Open your terminal or command prompt
3. Run the following commands based on your OS:

### Linux / macOS
Use `python3` and forward slashes (`/`) for paths
```sh
python3 "path/to/pt_priority.py" --sumo-config-path "/home/user/config.sumocfg" --prefer-lines "1"
```

### Windows
You can use `python` (or `py`) and backslashes (`\`) or forward slashes (`/`) for paths
```powershell
python "C:\path\to\pt_priority.py" --sumo-config-path "C:\Users\User\config.sumocfg" --prefer-lines "1"
```

## Common Errors

1. **`prefer-lines is required`**
   - **Fix**: Add the `--prefer-lines` argument with a comma-separated list of strings
2. **`Config path does not exist`**
   - **Fix**: Verify the file exists at the path provided
3. **`Invalid integer`**
   - **Fix**: Ensure `--until` and `--request-blocking-duration` are numbers (e.g., `3600`), not text

## Quick Tips
- **Quotes**: Always wrap the `--prefer-lines` value in quotes if it contains commas (e.g., `"1,2"`)
- **Default Values**: If you omit optional arguments, the script uses safe defaults (e.g., 3600 seconds for `--until`)
- **File Paths**: Using forward slashes (`/`) works on Windows, macOS, and Linux

## Accepted arguments
```sh
python3 "path/to/pt_priority.py" --help
```

| Argument | Description                                                                                                                       | Example                                       |
| :--- |:----------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------|
| `--sumo-config-path` | **Required**: Path to the configuration file                                                                                      | `--sumo-config-path /etc/sumo/config.sumocfg` |
| `--prefer-lines` | **Required**: Comma-separated list of lines to activate TLS                                                                       | `--prefer-lines "line1,line2"`                |
| `--tls-ids` | Optional: Comma-separated list of TLS IDs. Keep empty to include all TLS                                                          | `--tls-ids "J1,J2"`                           |
| `--flatpak` | Optional: Enable correct Flatpak command on Linux (flag only). No effect on Windows or macOS                                      | `--flatpak`                                   |
| `--until` | Optional: Run simulation until this time in seconds (Default: 3600).                                                              | `--until 7200`                                |
| `--tls-distance` | Optional: TLS activation distance threshold in meters (Default: 50).                                                              | `--tls-distance 100`                          |
| `--request-blocking-duration` | Optional: When one TLS request is active, block applying new requests to the same TLS, for the duration in seconds (Default: 10). | `--request-blocking-duration 30`              |
