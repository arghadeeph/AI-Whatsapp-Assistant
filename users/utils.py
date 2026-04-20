def get_business(user):
    return user.userbusiness_set.first().business