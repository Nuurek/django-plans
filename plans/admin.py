from copy import deepcopy

from django.contrib import admin
from django.urls import reverse
from ordered_model.admin import OrderedModelAdmin
from django.utils.translation import ugettext_lazy as _

from .models import Buyer, BuyerPlan, Plan, PlanQuota, Quota, PlanPricing, Pricing, Order, BillingInfo
from plans.models import Invoice


class PlanQuotaInline(admin.TabularInline):
    model = PlanQuota


class PlanPricingInline(admin.TabularInline):
    model = PlanPricing


class QuotaAdmin(OrderedModelAdmin):
    list_display = [
        'codename', 'name', 'description', 'unit',
        'is_boolean', 'move_up_down_links',
    ]

    list_display_links = list_display


def copy_plan(modeladmin, request, queryset):
    """
    Admin command for duplicating plans preserving quotas and pricings.
    """
    for plan in queryset:
        plan_copy = deepcopy(plan)
        plan_copy.id = None
        plan_copy.available = False
        plan_copy.default = False
        plan_copy.created = None
        plan_copy.save(force_insert=True)

        for pricing in plan.planpricing_set.all():
            pricing.id = None
            pricing.plan = plan_copy
            pricing.save(force_insert=True)

        for quota in plan.planquota_set.all():
            quota.id = None
            quota.plan = plan_copy
            quota.save(force_insert=True)


copy_plan.short_description = _('Make a plan copy')


class PlanAdmin(OrderedModelAdmin):
    search_fields = ('name', 'customized__name', 'customized__email', )
    list_filter = ('available', 'visible')
    list_display = [
        'name', 'description', 'customized', 'default', 'available',
        'created', 'move_up_down_links'
    ]
    list_display_links = list_display
    inlines = (PlanPricingInline, PlanQuotaInline)
    list_select_related = True
    raw_id_fields = ('customized',)
    actions = [copy_plan, ]

    def queryset(self, request):
        return super(PlanAdmin, self).queryset(request).select_related(
            'customized'
        )


class BillingInfoAdmin(admin.ModelAdmin):
    search_fields = ('buyer__name', 'buyer__email', 'tax_number', 'name')
    list_display = ('buyer', 'tax_number', 'name', 'street', 'zipcode', 'city', 'country')
    list_display_links = list_display
    list_select_related = True
    exclude = ('buyer',)


def make_order_completed(modeladmin, request, queryset):
    for order in queryset:
        order.complete_order()


make_order_completed.short_description = _('Make selected orders completed')


def make_order_invoice(modeladmin, request, queryset):
    for order in queryset:
        if Invoice.objects.filter(type=Invoice.INVOICE_TYPES['INVOICE'], order=order).count() == 0:
            Invoice.create(order, Invoice.INVOICE_TYPES['INVOICE'])


make_order_invoice.short_description = _('Make invoices for orders')


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_filter = ('status', 'created', 'completed', 'plan__name', 'pricing')
    raw_id_fields = ('buyer',)
    search_fields = (
        'id', 'buyer__name', 'buyer__email', 'invoice__full_number'
    )
    list_display = (
        'id', 'name', 'created', 'buyer', 'status', 'completed',
        'tax', 'amount', 'currency', 'plan', 'pricing'
    )
    list_display_links = list_display
    actions = [make_order_completed, make_order_invoice]
    inlines = (InvoiceInline, )

    def queryset(self, request):
        return super(OrderAdmin, self).queryset(request).select_related('plan', 'pricing', 'buyer')


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = (
        'full_number', 'buyer_tax_number',
        'buyer__name', 'buyer__email'
    )
    list_filter = ('type', 'issued')
    list_display = (
        'full_number', 'issued', 'total_net', 'currency', 'buyer',
        'tax', 'buyer_name', 'buyer_city', 'buyer_tax_number'
    )
    list_display_links = list_display
    list_select_related = True
    raw_id_fields = ('buyer', 'order')


class BuyerPlanAdmin(admin.ModelAdmin):
    list_filter = ('active', 'expire', 'plan__name', 'plan__available', 'plan__visible',)
    search_fields = ('buyer__name', 'buyer__email', 'plan__name',)
    list_display = ('buyer', 'plan', 'expire', 'active')
    list_display_links = list_display
    list_select_related = True
    fields = ('buyer', 'plan', 'expire', 'active',)
    raw_id_fields = ['plan']


admin.site.register(Buyer)
admin.site.register(Quota, QuotaAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(BuyerPlan, BuyerPlanAdmin)
admin.site.register(Pricing)
admin.site.register(Order, OrderAdmin)
admin.site.register(BillingInfo, BillingInfoAdmin)
admin.site.register(Invoice, InvoiceAdmin)
