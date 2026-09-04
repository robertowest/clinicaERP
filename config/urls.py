from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.usuarios.api.endpoints import MeView
from apps.usuarios.views import LoginPorRolView
from config.router import router

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', LoginPorRolView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/v1/auth/me/', MeView.as_view(), name='auth-me'),
    path('api/v1/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('', login_required(TemplateView.as_view(template_name='home.html')), name='home'),

    path('organizacion/', include('apps.organizacion.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('pacientes/', include('apps.pacientes.urls')),
    path('medicos/', include('apps.medicos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
