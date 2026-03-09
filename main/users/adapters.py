from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        extra_data = sociallogin.account.extra_data

        first_name = extra_data.get("given_name", "")
        last_name = extra_data.get("family_name", "")
        picture_url = extra_data.get("picture")

        fields_to_update = []

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            fields_to_update.append("first_name")

        if last_name and user.last_name != last_name:
            user.last_name = last_name
            fields_to_update.append("last_name")

        if picture_url and user.profile_image != picture_url:
            user.profile_image = picture_url
            fields_to_update.append("profile_image")

        if user.pk and fields_to_update:
            user.save(update_fields=fields_to_update)

        super().pre_social_login(request, sociallogin)