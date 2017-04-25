from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, Client


class LiaisonViewTests(TestCase):
    def setUp(self):
        self.url = reverse('people:liaison_create')

    def test_create_liaison_url_exists(self):
        resolve(self.url)

    def test_create_liaison_view_renders(self):
        c = Client()
        with self.assertTemplateUsed('people/liaison_form.html'):
            c.get(self.url)
