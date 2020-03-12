IoTtalk v2 Python SDK
===============================================================================

Current supported module:

- Device Application to Network (DAN)
- Device Application to IoT device (DAI)

Supported Python version:

- 2.7
- 3.4+


Installation
----------------------------------------------------------------------

::

    pip install iottalk-py


Usage of DAI module
----------------------------------------------------------------------

There is a executable DAI module. User can invoke it via the command line
interface.::

    python -m iottalkpy.dai /path/to/your/sa.py

or::

    python -m iottalkpy.dai /path/to/your/sa# in case of dir


API
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

If you want to operate DAI via Python API:

.. code-block:: python

    from iottalkpy import dai

    sa = dai.module_to_sa(dai.load_module('/path/to/sa.py'))
    sa.start()
    ...
    # stop sa process
    sa.terminate()


Usage of DAN module
----------------------------------------------------------------------

Minimal example:

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


Developer Notes
----------------------------------------------------------------------

Release steps

#. Bump version and commit

#. ``git-tag`` the version

#. ``git push --tags``

#. ``python ./setup.py bdist_wheel``

#. ``twine upload ./dist/iottalk_py-<version>-py3-none-any.whl``


TODO
----------------------------------------------------------------------

#. Auto generate doc via Sphinx
