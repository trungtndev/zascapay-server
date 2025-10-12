from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class UserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse('user-list')  # from DRF router

    def test_create_user_success(self):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'secret123',
            'first_name': 'Alice',
            'last_name': 'Liddell',
        }
        res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', res.data)
        user = User.objects.get(id=res.data['id'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('secret123'))

    def test_create_user_rejects_admin_flags(self):
        payload = {
            'username': 'bob',
            'password': 'secret123',
            'is_staff': True,
        }
        res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_non_admin_users(self):
        u1 = User.objects.create_user(username='u1', password='p1')
        u2 = User.objects.create_user(username='u2', password='p2')
        admin = User.objects.create_superuser(username='admin', password='adminpass')
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in res.data]
        self.assertIn('u1', usernames)
        self.assertIn('u2', usernames)
        self.assertNotIn('admin', usernames)

    def test_retrieve_update_partial_delete_flow(self):
        # Create
        res = self.client.post(self.list_url, {'username': 'charlie', 'password': 'pw'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user_id = res.data['id']
        detail_url = reverse('user-detail', args=[user_id])
        # Retrieve
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'charlie')
        # Update
        res = self.client.put(detail_url, {'username': 'charlie2', 'password': 'pw2'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'charlie2')
        # Partial update
        res = self.client.patch(detail_url, {'first_name': 'C'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['first_name'], 'C')
        # Delete
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        # Ensure gone
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
