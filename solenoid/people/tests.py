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


class DLCTests(TestCase):
    fixtures = ['records.yaml']

    def setUp(self):
        self.url = reverse('people:dlc_update')
        self.client = Client()

    def _get_form_data(self):
        orig_count = DLC.objects.count()
        data = {'form-TOTAL_FORMS': [str(orig_count + 3)],
                'form-INITIAL_FORMS': [str(orig_count)]}
        counter = 0
        for dlc in DLC.objects.all():
            data['form-%d-name' % counter] = [dlc.name.replace('and', '&')]
            data['form-%d-id' % counter] = [str(dlc.pk)]
            counter += 1

        return data

    def test_can_edit_dlcs_on_list_page(self):
        """Posting the form will change existing DLCs."""
        orig_count = DLC.objects.count()

        data = self._get_form_data()
        self.client.post(self.url, data)

        # We didn't add any DLCs in the form, so we shouldn't have created any.
        self.assertEqual(orig_count, DLC.objects.count())

        dlc_names = DLC.objects.all().values_list('name', flat=True)
        self.assertIn('Brain & Cognitive Sciences Department', dlc_names)
        self.assertIn('Electrical Engineering & Computer Science Department',
                      dlc_names)

        self.assertNotIn('Brain and Cognitive Sciences Department', dlc_names)
        self.assertNotIn(
            'Electrical Engineering and Computer Science Department',
            dlc_names)

    def test_can_add_dlcs(self):
        """Posting the form with data in the new DLC blanks will add DLCs."""
        orig_count = DLC.objects.count()

        data = self._get_form_data()
        data['form-%d-name' % orig_count] = ['Shiny new DLC']
        data['form-%d-id' % orig_count] = ['']
        self.client.post(self.url, data)

        self.assertEqual(orig_count + 1, DLC.objects.count())

        dlc_names = DLC.objects.all().values_list('name', flat=True)
        self.assertIn('Shiny new DLC', dlc_names)

    def test_can_create_DLC_without_liaison(self):
        DLC.objects.create(name='Test DLC')
