def get_business_id(request):
    """
    Returns business_id from request — attached by TenantMiddleware.
    Falls back to querying DB if middleware didn't attach it (e.g. on HTML pages).
    """
    # Fast path — middleware already attached it
    if hasattr(request, 'business_id'):
        return request.business_id

    # Fallback for non-API views
    from users.models import UserBusiness
    from rest_framework.exceptions import PermissionDenied
    
    user_business = (
        UserBusiness.objects
        .filter(user=request.user)
        .values_list('business_id', flat=True)
        .first()
    )
    if not user_business:
        raise PermissionDenied("No business associated with this account.")
    return user_business