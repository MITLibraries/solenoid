import hashlib

from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, Client, override_settings

from .models import Liaison, DLC, Author
from .views import LiaisonList


@override_settings(LOGIN_REQUIRED=False)
class LiaisonCreateViewTests(TestCase):
    fixtures = ['testdata.yaml']

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


@override_settings(LOGIN_REQUIRED=False)
class LiaisonDeletionTests(TestCase):
    fixtures = ['testdata.yaml']

    def setUp(self):
        self.client = Client()

    def test_create_liaison_url_exists(self):
        resolve(reverse('people:liaison_delete', args=(1,)))

    def test_delete_view_1(self):
        """Delete view works for a liaison without attached emails."""
        response = self.client.post(reverse('people:liaison_delete',
                                            args=(2,)))
        self.assertRedirects(response, reverse('people:liaison_list'))
        self.assertFalse(Liaison.objects.filter(pk=2))
        self.assertFalse(Liaison.objects_all.filter(pk=2))

    def test_delete_view_2(self):
        """Delete view works for a liaison with attached emails."""
        response = self.client.post(reverse('people:liaison_delete',
                                            args=(1,)))
        self.assertRedirects(response, reverse('people:liaison_list'))
        self.assertFalse(Liaison.objects.filter(pk=1))
        self.assertTrue(Liaison.objects_all.filter(pk=1))

    def test_queryset_delete(self):
        qs = Liaison.objects.filter(pk__in=[1, 2])
        qs.delete()
        self.assertEqual(Liaison.objects.filter(pk__in=[1, 2]).count(), 0)
        self.assertEqual(Liaison.objects_all.filter(pk__in=[1, 2]).count(), 1)


@override_settings(LOGIN_REQUIRED=False)
class LiaisonListTests(TestCase):
    fixtures = ['testdata.yaml']

    def test_queryset(self):
        """Make sure inactive liaisons don't show."""
        liaison = Liaison.objects.latest('pk')
        liaison.active = False
        liaison.save()

        count_all = Liaison.objects_all.count()
        count_visible = Liaison.objects.count()
        assert count_visible < count_all

        for liaison in Liaison.objects.all():
            assert liaison in LiaisonList().queryset

        for liaison in LiaisonList().queryset:
            assert liaison in Liaison.objects.all()


@override_settings(LOGIN_REQUIRED=False)
class LiaisonUpdateTests(TestCase):
    fixtures = ['testdata.yaml']

    def test_queryset(self):
        """Make sure inactive liaisons can't be updated."""
        liaison = Liaison.objects.latest('pk')
        liaison.active = False
        liaison.save()

        c = Client()
        response = c.get(reverse('people:liaison_update', args=(liaison.pk,)))
        assert response.status_code == 404


@override_settings(LOGIN_REQUIRED=False)
class DLCTests(TestCase):

    # We used to have an option for letting people manually edit DLCs. We've
    # backed this out in favor of only creating DLCs via CSV import - there
    # is name authority work going on upstream we would prefer to rely on.
    # If it's desirable to put that functionality back, there were tests for it
    # here, and it last existed at commit
    # 489ec2a7f2c921db0cdcaa6d05cf733865c4315d.
    def test_can_create_DLC_without_liaison(self):
        DLC.objects.create(name='Test DLC')


@override_settings(LOGIN_REQUIRED=False)
class AuthorTests(TestCase):
    def tearDown(self):
        Author.objects.all().delete()
        DLC.objects.all().delete()

    def test_mit_id_is_hashed(self):
        """Storing the MIT ID directly on Heroku would violate the sensitive
        data policy, but we don't need to maintain it; its only value is as a
        unique key, so hashing it and storing the hash is fine;
        http://infoprotect.mit.edu/what-needs-protecting . Note that MIT IDs in
        test data files are already fake and thus not sensitive."""
        dlc = DLC.objects.create(name='Test DLC')
        mit_id = '000000000'
        author = Author.objects.create(dlc=dlc,
            email='foo@example.com',
            first_name='Test',
            last_name='Author',
            mit_id=mit_id)

        self.assertEqual(author.mit_id,
                         hashlib.md5(mit_id.encode('utf-8')).hexdigest())

    def test_mit_id_is_not_stored(self):
        """No matter what properties we end up putting on Author, none of them
        are the MIT ID."""
        dlc = DLC.objects.create(name='Test DLC')
        mit_id = '000000000'
        author = Author.objects.create(dlc=dlc,
            email='foo@example.com',
            first_name='Test',
            last_name='Author',
            mit_id=mit_id)

        author_fields = Author._meta.get_fields()

        for field in author_fields:
            if field.is_relation is False:
                self.assertNotEqual(getattr(author, field.name), mit_id)

    def test_author_set_hash(self):
        dlc = DLC.objects.create(name='Test DLC')
        author = Author.objects.create(dlc=dlc,
            email='foo@example.com',
            first_name='Test',
            last_name='Author',
            mit_id='000000000')

        new_mit_id = '214915295'

        author.mit_id = new_mit_id
        author.save()
        self.assertEqual(author.mit_id,
                         hashlib.md5(new_mit_id.encode('utf-8')).hexdigest())

    def test_author_get_hash(self):
        mit_id = '214915295'

        self.assertEqual(Author.get_hash(mit_id),
                         hashlib.md5(mit_id.encode('utf-8')).hexdigest())


class LiaisonModelTests(TestCase):
    fixtures = ['testdata.yaml']

    def test_filter_only_shows_active(self):
        self.assertEqual(Liaison.objects.count(), 3)
        l3 = Liaison.objects.get(pk=3)
        l3.active = False
        l3.save()
        self.assertEqual(Liaison.objects.count(), 2)

    def test_setting_inactive_unsets_DLCs(self):
        l1 = Liaison.objects.get(pk=1)
        self.assertTrue(l1.dlc_set.count())
        l1.active = False
        l1.save()
        self.assertFalse(l1.dlc_set.count())

    def test_deleting_liaison_with_emails_sets_to_inactive(self):
        l1 = Liaison.objects.get(pk=1)  # This one has an EmailMessage
        l1.delete()
        self.assertFalse(l1.active)

    def test_deleting_liaison_without_emails_behaves_normally(self):
        l2 = Liaison.objects.get(pk=2)  # This one does not have EmailMessages

        # This should raise no error.
        l2.delete()

        self.assertFalse(Liaison.objects.filter(pk=2))
