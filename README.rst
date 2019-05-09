IoTtalk v2 Python SDK
===============================================================================

Current supported module:

- Device Application to Network (DAN)


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
