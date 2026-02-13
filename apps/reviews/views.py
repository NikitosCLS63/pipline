from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from apps.reviews.models import Reviews
from apps.users.models import Customers
from apps.products.models import Products


def _get_request_customer(request):
	
	# 1) django user -> customer
	user = getattr(request, 'user', None)
	if user and hasattr(user, 'customer') and user.customer:
		return user.customer

	# 2) middleware-provided JWT customer id
	customer_id = getattr(request, 'jwt_customer_id', None)
	if customer_id:
		try:
			return Customers.objects.get(customer_id=customer_id)
		except Customers.DoesNotExist:
			pass

	# 3) cookie
	try:
		cid = request.COOKIES.get('customer_id')
		if cid:
			return Customers.objects.filter(customer_id=int(cid)).first()
	except Exception:
		pass

	return None


def reviews_page(request):
	"""Render reviews page with product_id and current_customer_id in context.
	If no product_id, show all reviews by current user."""
	product_id = request.GET.get('product_id')
	context = {'product_id': product_id}

	customer = _get_request_customer(request)
	if customer:
		context['current_customer_id'] = customer.customer_id
		# Get all reviews by this customer if no product_id specified
		if not product_id:
			user_reviews = Reviews.objects.filter(customer=customer).select_related('product').order_by('-publication_date')
			context['user_reviews'] = user_reviews

	return render(request, 'reviews.html', context)


@csrf_exempt
def submit_review(request):
	if request.method != 'POST':
		return HttpResponseNotAllowed(['POST'])

	customer = _get_request_customer(request)
	if not customer:
		return JsonResponse({'error': 'Authentication required'}, status=401)

	try:
		import json
		data = json.loads(request.body.decode('utf-8'))
		product_id = int(data.get('product_id'))
		rating = int(data.get('rating'))
		comment = data.get('reviews_comment', '').strip()
	except Exception:
		return HttpResponseBadRequest('Invalid payload')

	try:
		product = Products.objects.get(product_id=product_id)
	except Products.DoesNotExist:
		return JsonResponse({'error': 'Product not found'}, status=404)

	# Check for existing review by this customer for this product
	existing = Reviews.objects.filter(product=product, customer=customer).first()
	if existing:
		return JsonResponse({'error': 'Review already exists'}, status=400)

	review = Reviews.objects.create(
		product=product,
		customer=customer,
		rating=rating,
		reviews_comment=comment,
		publication_date=timezone.now(),
		status='published'
	)

	return JsonResponse({'review_id': review.review_id, 'message': 'Created'}, status=201)


@csrf_exempt
def edit_review(request, review_id):
	if request.method not in ('POST', 'PUT', 'PATCH'):
		return HttpResponseNotAllowed(['POST', 'PUT', 'PATCH'])

	customer = _get_request_customer(request)
	if not customer:
		return JsonResponse({'error': 'Authentication required'}, status=401)

	try:
		review = Reviews.objects.get(review_id=review_id)
	except Reviews.DoesNotExist:
		return JsonResponse({'error': 'Review not found'}, status=404)

	if review.customer != customer:
		return HttpResponseForbidden('Not allowed')

	try:
		import json
		data = json.loads(request.body.decode('utf-8'))
		rating = int(data.get('rating', review.rating))
		comment = data.get('reviews_comment', review.reviews_comment)
	except Exception:
		return HttpResponseBadRequest('Invalid payload')

	review.rating = rating
	review.reviews_comment = comment
	review.publication_date = timezone.now()
	review.save()

	return JsonResponse({'review_id': review.review_id, 'message': 'Updated'})


@csrf_exempt
def delete_review(request, review_id):
	if request.method not in ('POST', 'DELETE'):
		return HttpResponseNotAllowed(['POST', 'DELETE'])

	customer = _get_request_customer(request)
	if not customer:
		return JsonResponse({'error': 'Authentication required'}, status=401)

	try:
		review = Reviews.objects.get(review_id=review_id)
	except Reviews.DoesNotExist:
		return JsonResponse({'error': 'Review not found'}, status=404)

	if review.customer != customer:
		return HttpResponseForbidden('Not allowed')

	review.delete()
	return JsonResponse({'message': 'Deleted'})
