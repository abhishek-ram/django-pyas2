# -*- coding: utf-8 -*-
from django.apps import AppConfig


class Pyas2Config(AppConfig):
    name = 'pyas2'
    verbose_name = 'pyAS2 File Transfer Server'

    def ready(self):
        super(Pyas2Config, self).ready()
