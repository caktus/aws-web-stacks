Contributing
============

Troposphere and CloudFormation open up many possibilities, and we're open to any
contributions that expand the flexibility of this project within its overall mission.

To contribute, you'll need Python 3.5 and a virtual environment with our requirements
installed.

Setup
-----

.. code-block:: bash

    mkvirtualenv -p python3.8 aws-web-stacks
    pip install -r requirements.txt
    pip install -U pre-commit
    # Optionally install git pre-commit hook:
    pre-commit install

Check Code Formatting
---------------------

If you have the pre-commit hook installed per the above, code formatting will be checked
automatically with each commit. You can optionally run all checks manually as well:

.. code-block:: bash

    pre-commit run --all-files

Compile YAML Templates
----------------------

.. code-block:: bash

    make

The templates will be saved to the ``content/`` directory.

Building the documentation
--------------------------

.. code-block:: bash

    cd docs
    make html

The docs will be available in the ``docs/_build/html/`` directory.

Submitting Pull Requests
------------------------

**Please follow these basic steps to simplify pull request reviews.**

* Please rebase your branch against the current ``main`` branch
* Please ensure pre-commit checks and ``make`` (see above) succeed before submitting a PR
* Make reference to possible `issues <https://github.com/caktus/aws-web-stacks/issues>`_ on PR comment

Submitting bug reports
----------------------

* Please include the exact filename of the template used
* Please include any and all error messages generated by AWS

Release Process
---------------

* Merge any PRs targeted for the release into the ``main`` branch.

* Write release notes in the `changelog <https://github.com/caktus/aws-web-stacks/blob/main/CHANGELOG.rst>`_,
  including:

  * links to PRs as appropriate
  * credit for outside contributors
  * a link (at the bottom of the file) to the listing page in the ``aws-web-stacks`` bucket

  It may help to view the changes since the last release::

      git diff -r v2.0.0

* Tag the release in Git and push it to GitHub, e.g.::

      git checkout main && git pull
      git tag -a v2.1.0 -m "v2.1.0"
      git push origin v2.1.0

* After pushing a version tag, Actions will:

  * create a release on GitHub
  * build the template YAML files
  * add the templates as an asset to the release
  * upload the templates to S3

  The current, stable (unversioned) releases will be overwritten, and a copy of the release will
  be archived to a folder named for the version in the S3 bucket.

* Navigate to the Releases tab in GitHub and edit the release for the tag just pushed to include
  a copy of the release notes.
