test:
	@(py.test --cov-report term --cov-config .coveragerc --cov=pyas2 --color=yes pyas2/tests/ -k 'not concurrency')

serve:
	@(ENV=example python manage.py migrate && python manage.py runserver)

release:
	@(python setup.py bdist_wheel register upload -s)