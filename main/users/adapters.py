from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        picture_url = sociallogin.socialaccount.extra_data.get("picture")
        if picture_url and user.profile_image != picture_url:
            user.profile_image = picture_url
            user.save(update_fields=["profile_image"])
            
        return user