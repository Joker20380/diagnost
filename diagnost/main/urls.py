from django.urls import path, re_path
from django.views.decorators.csrf import csrf_exempt
from .views import *

urlpatterns = [
                path('', Index.as_view(), name='index'),
                path('about/', About.as_view(), name='about'),
                path('news/<slug:news_slug>/', ShowNews.as_view(), name='news'),
                path('doc/<slug:doc_slug>/', ShowDoc.as_view(), name='doc'),
                path('project/<slug:project_slug>/', ShowProject.as_view(), name='project'),
                path('lecture/<slug:lecture_slug>/', ShowLecture.as_view(), name='lecture'),
                path('projects/', Projects.as_view(), name='projects'),
                path('blog/', Blog.as_view(), name='blog'),
                path('subscribe/', Subscribe, name='subscribe'),
                path('unsubscribe/', Unsubscribe, name='unsubscribe_request'),
    			path('unsubscribe/confirm/<str:token>/', Unsubscribe_confirm, name='unsubscribe_confirm'),
    			path('contacts/', ContactsView.as_view(), name='contacts'),
    			path("sitemap.xml", SitemapXmlView.as_view(), name="sitemap"),
    			path("yandex_d263e56262d9ffc1.html", YandexView.as_view()),
    			path("robots.txt", RobotsTxtView.as_view()),
    			path('conf/', Conf.as_view(), name='conf'),
    			path('upload/', upload_diagnostic, name='diagnostic_upload'),
    			path('session/<int:session_id>/', diagnostic_detail, name='diagnostic_detail'),
    			path('suspension/<int:session_id>/', suspension_inspection, name='suspension_inspection'),


                
              ]