IoTtalk v2 Python SDK
===============================================================================

Current supported module:

- Device Application to Network (DAN)

Supported Python version:

- 3.5
- 3.6
- 3.7


Installation
----------------------------------------------------------------------

::

    pip install iottalk-py


Usage
----------------------------------------------------------------------

Minimal example

.. code-block:: python

    from iottalkpy import dan

    ccm_url = 'http://localhost:9992'

    def on_data(*args):
        ...

    def on_signal(*args):
        ...  # handle CCM signal here

    client = dan.Client()
    client.register(
        ccm_url,
        on_signal=on_signal,
        on_data=on_data
        odf_list=[('meow', ['dB'])],
        name='BetaCat',
        profile={
            'model': 'AI',
        },
    )
    client.loop_forever()


TODO
----------------------------------------------------------------------

#. Auto generate doc via Sphinx
