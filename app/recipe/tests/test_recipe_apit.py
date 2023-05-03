"""Tests for Recipe API"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Helper function to create a recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'description': 'Sample description',
        'link': 'https://www.google.com'
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


def create_user(**params):
    """Helper function to create a user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='testpass',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = create_user(
            email='user2@example.com',
            password='testpass'
        )

        create_recipe(user=user2)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 5.00,
        }
        response = self.client.post(RECIPES_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=response.data['id'])
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test updating a recipe partially"""
        original_link = 'https://www.google.com'
        recipe = create_recipe(user=self.user, link=original_link)
        payload = {
            'title': 'Chocolate cheesecake',
            'link': 'https://www.yahoo.com',
        }

        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, payload['link'])
        self.assertEqual(recipe.time_minutes, recipe.time_minutes)
        self.assertEqual(recipe.price, recipe.price)
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test full update of recipe"""
        recipe = create_recipe(
            user=self.user,
            title='Spaghetti carbonara',
            link='https://www.google.com',
            description='Sample description',
        )

        payload = {
            'title': 'New Spaghetti carbonara',
            'time_minutes': 25,
            'price': Decimal('7.00'),
            'link': 'https://www.yahoo.com',
            'description': 'New Sample description',
        }

        url = detail_url(recipe.id)
        response = self.client.put(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test that updating user returns error"""
        user2 = create_user(
            email='user2.example.com',
            password='testpass',
        )

        recipe = create_recipe(user=self.user)
        payload = {
            'user': user2.id,
        }

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_other_users_recipe_error(self):
        """Test that other users cannot delete recipe"""
        user2 = create_user(
            email='user2@example.com',
            password='testpass',
        )

        recipe = create_recipe(user=user2)

        url = detail_url(recipe.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags"""
        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [{'name': 'vegan'}, {'name': 'dessert'}],
            'time_minutes': 60,
            'price': Decimal('20.00'),
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test creating a recipe with existing tag"""
        tag = Tag.objects.create(user=self.user, name='vegan')
        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [{'name': tag.name}, {'name': 'dessert'}],
            'time_minutes': 60,
            'price': Decimal('20.00'),
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag on update"""
        recipe = create_recipe(user=self.user)
        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [{'name': 'dessert'}],
            'time_minutes': 60,
            'price': Decimal('20.00'),
        }

        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='dessert')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test updating a recipe and assigning a tag"""
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='dessert')
        recipe.tags.add(tag)

        tag_lunch = Tag.objects.create(user=self.user, name='lunch')
        payload = {
            'tags': [{'name': 'lunch'}],
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag, recipe.tags.all())

    def test_clear_recipe_tag(self):
        """Test clearing a recipe tag"""
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='dessert')
        recipe.tags.add(tag)

        payload = {
            'tags': [],
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating recipe with new ingredients"""
        payload = {
            'title': 'Thai prawn red curry',
            'ingredients': [
                {'name': 'prawns'},
                {'name': 'coconut milk'},
                {'name': 'red curry paste'},
            ],
            'time_minutes': 20,
            'price': Decimal('7.00'),
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 3)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating recipe with existing ingredients"""
        ingredient = Ingredient.objects.create(
            user=self.user, name='prawns')
        payload = {
            'title': 'Thai prawn red curry',
            'ingredients': [
                {'name': 'prawns'},
                {'name': 'coconut milk'},
                {'name': 'red curry paste'},
            ],
            'time_minutes': 20,
            'price': Decimal('7.00'),
        }
        response = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 3)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredients_on_updated(self):
        """Test creating ingredients on update"""
        recipe = create_recipe(user=self.user)
        payload = {
            'ingredients': [
                {'name': 'prawns'},
            ],
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='prawns')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test updating a recipe and assigning an ingredient"""
        recipe = create_recipe(user=self.user)
        ingredient = Ingredient.objects.create(user=self.user, name='prawns')
        recipe.ingredients.add(ingredient)

        ingredient2 = Ingredient.objects.create(
            user=self.user, name='coconut milk')

        payload = {
            'ingredients': [
                {'name': 'coconut milk'},
            ],
        }

        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe ingredients"""
        recipe = create_recipe(user=self.user)
        ingredient = Ingredient.objects.create(
            user=self.user, name='prawns')
        recipe.ingredients.add(ingredient)

        payload = {
            'ingredients': [],
        }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)
