# Shared Resources Demo

This repository demonstrates shared resources by having a deployed applicataion opt in to an unknown ASA within the group transaction. The application call does not require the asset ID to be included as a foreign asset, rather it looks at the transaction following it and if it's being sent to the application's address it will opt into it if it's not already opted in.

## Usage

To run through the demo make sure you have a sandbox environment running, then modify `main.py` to include your token/server, along with a funded account mnemonic. Then you can run the script to perform a complete run through.

```bash
$ ./main.py
```

## Steps taken in main.py

1. Deploy Application
2. Fund Application Account
3. Create new ASA
4. Send group transaction consisting of an application call and an axfer of the ASA to the application address.

