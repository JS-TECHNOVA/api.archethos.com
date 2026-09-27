from django.contrib import admin

from .models import Company, Enquiry, EnquiryReply


admin.site.register([Company, Enquiry, EnquiryReply])
