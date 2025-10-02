# DjangoShellyElectiricityAutomation Docker Usage Guide
# First-Time Project Setup

## 1. Create a Python Virtual Environment (venv)
```bash
python3 -m venv venv
```

## 2. Activate the Virtual Environment
- On Linux/macOS:
	```bash
	source venv/bin/activate
	```
- On Windows:
	```cmd
	venv\Scripts\activate
	```

## 3. Install Project Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Select Python Interpreter in VS Code
- Open the Command Palette (`Ctrl+Shift+P`)
- Type and select `Python: Select Interpreter`
- Choose the interpreter from your `venv` folder (e.g., `venv/bin/python` or `venv\Scripts\python.exe`)

## Overview
This project uses Docker for both production and test environments. Two shell scripts are provided to build and run the containers:
- `docker-prod.sh` for production
## Running the Docker Scripts

### 1. Production
To build and run the production container:
```bash
bash docker-prod.sh
```
- The app will run on port 8000.
- Persistent data is stored in the `data/` folder in your project root.

### 2. Test
To build and run the test container:
```bash
bash docker-test.sh
```
- The app will run on port 9000.
- Persistent data is stored in the `data-test/` folder in your project root.

## Versioning

- The Docker image version is read from the `VERSION` file in the project root.
- Each build appends the current date and time (with seconds) to the version (e.g., `1.0.0-20251002-164123`).
- All built images are available and selectable by their tag.

### Changing the Version
1. Edit the `VERSION` file and set your desired version (use [semver2](https://semver.org/) format, e.g., `1.2.3`).
2. Run either script to build a new image with the updated version.

## Listing Available Versions
To list all available Docker image versions for test or prod:
```bash
docker images django-shelly-test
docker images django-shelly-prod
```


## Running a Specific Version
To run a specific test version (tag):
```bash
docker run -d -p 9000:8000 django-shelly-test:1.0.0-20251002-164123
```
To run a specific production version (tag):
```bash
docker run -d -p 8000:8000 django-shelly-prod:1.0.0-20251002-164123
```
Replace the tag with the desired version (including seconds).


## Default Django Admin Credentials
- Username: `admin`
- Password: `admin12345`

## Notes
- The scripts automatically stop and remove any existing container with the same name before starting a new one.
- Data is persistent between runs as long as you do not delete the `data/` or `data-test/` folders.
- For production, consider using a real database instead of SQLite for better reliability and scalability.
