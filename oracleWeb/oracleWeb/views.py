from django.http import HttpResponse

def test_page(request):

    html = "<html><body>This is a test page.</body></html>"

    return HttpResponse(html)