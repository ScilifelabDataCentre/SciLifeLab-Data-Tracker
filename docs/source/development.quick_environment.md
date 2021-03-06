# System for development

## Prepare config file

Prepare a `config.yaml` file. Just renaming `config.yaml.sample` to `config.yaml` and setting the two `dev` variables to true should be enough.

## Build and activate the containers

```
docker-compose up
```

The system can be accessed in a web browser at `localhost:5000`.

## Add test data

Set a virtual Python environment, install modules.
```
python -m venv venv
. venv/bin/activate
pip install -r test/requirements.txt
pip install -r backend/requirements.txt
```

Randomized test data can be generated by `test/gen_test_db.py`. Run it using e.g.:

```
PYTHONPATH=backend python3 test/gen_test_db.py
```
