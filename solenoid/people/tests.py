from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, Client

from .models import Liaison, DLC


class LiaisonViewTests(TestCase):
    fixtures = ['records.yaml']

    def setUp(self):
        self.url = reverse('people:liaison_create')
        self.client = Client()

    def test_create_liaison_url_exists(self):
        resolve(self.url)

    def test_create_liaison_view_renders(self):
        with self.assertTemplateUsed('people/liaison_form.html'):
            self.client.get(self.url)

    def test_submit_liaison_form_creates_liaison_with_dlcs(self):
        first_name = 'Anastasius'
        last_name = 'Bibliotecarius'
        email_address = 'ab@example.com'

        self.client.post(self.url, {'first_name': first_name,
                                    'last_name': last_name,
                                    'email_address': email_address,
                                    'dlc': [1, 2]})

        liaison = Liaison.objects.latest('pk')
        self.assertEqual(liaison.first_name, first_name)
        self.assertEqual(liaison.last_name, last_name)
        self.assertEqual(liaison.email_address, email_address)
        self.assertEqual(liaison.dlc_set.count(), 2)
        self.assertIn(DLC.objects.get(pk=1), liaison.dlc_set.all())
        self.assertIn(DLC.objects.get(pk=2), liaison.dlc_set.all())
