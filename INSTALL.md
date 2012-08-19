## Installation ##

- Copy data/config.default.py to data/config.py
- Edit config.py, NOT config.default.py to your liking

If you want to use Tornado as your WSGI server:

- Change the port/address in tornado.start.py as needed
- Run tornado.start.py

If you use a different WSGI server:

- Instantiate a PyBoard object
- Configure the endpoint (the `application()` method) to the PyBoard object's `__call__` method
- Start the server
