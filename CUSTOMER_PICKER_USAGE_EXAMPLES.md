# CustomerPicker - Ejemplos de Uso

## Ejemplo 1: Scheduled Documents

```typescript
import { CustomerPicker } from '@/components/customers/CustomerPicker';
import { CustomerFormValues } from '@/components/customers/CustomerPicker/CustomerPicker.types';

function ScheduledDocumentForm() {
    const [formData, setFormData] = useState({
        dte_type_id: '33',
        receiver_id: null,
        receiver_tax_id: '',
        receiver_name: '',
        receiver_business_name: '',
        customer_addresses: [],
        customer_activities: [],
        // ...
    });

    const [customers, setCustomers] = useState([]);
    const [isLoadingCustomers, setIsLoadingCustomers] = useState(false);

    const handleCustomerChange = (values: CustomerFormValues) => {
        setFormData(prev => ({
            ...prev,
            receiver_id: values.id,
            receiver_tax_id: values.taxId,
            receiver_name: values.name,
            receiver_business_name: values.businessName,
            receiver_address: values.address,
            receiver_city: values.city,
            receiver_district: values.district,
            customer_economic_activity: values.activityName,
            customer_activity_code: values.activityCode,
            selected_address_id: values.selectedAddressId,
            selected_activity_id: values.selectedActivityId,
        }));
    };

    const handleSearch = async (term: string) => {
        if (!term.trim()) return;
        
        setIsLoadingCustomers(true);
        try {
            const response = await api.get(`/master-entities/${entityId}/customers/?search=${term}`);
            const data = await response.json();
            setCustomers(data.results || []);
        } finally {
            setIsLoadingCustomers(false);
        }
    };

    return (
        <CustomerPicker
            documentType={formData.dte_type_id}
            defaultValues={{
                id: formData.receiver_id,
                taxId: formData.receiver_tax_id,
                name: formData.receiver_name,
                businessName: formData.receiver_business_name,
                address: formData.receiver_address,
                city: formData.receiver_city,
                district: formData.receiver_district,
                activityName: formData.customer_economic_activity,
                activityCode: formData.customer_activity_code,
                selectedAddressId: formData.selected_address_id,
                selectedActivityId: formData.selected_activity_id,
            }}
            addresses={formData.customer_addresses}
            activities={formData.customer_activities}
            customers={customers}
            isLoadingCustomers={isLoadingCustomers}
            onCustomerChange={handleCustomerChange}
            onSearch={handleSearch}
        />
    );
}
```

## Ejemplo 2: Multi Invoice Wizard

```typescript
import { CustomerPicker } from '@/components/customers/CustomerPicker';
import { useForm, useWatch } from 'react-hook-form';

function MultiInvoiceWizard() {
    const form = useForm();
    const activeDocIndex = 0;
    const documentType = useWatch({ control: form.control, name: `documents.${activeDocIndex}.dte_type_id` });
    const customerData = useWatch({ control: form.control, name: `documents.${activeDocIndex}.customer` });

    const handleCustomerChange = (values: CustomerFormValues) => {
        form.setValue(`documents.${activeDocIndex}.customer`, values, { shouldDirty: true });
    };

    return (
        <CustomerPicker
            documentType={documentType}
            defaultValues={customerData}
            addresses={customerData?.addresses || []}
            activities={customerData?.activities || []}
            customers={customers}
            onCustomerChange={handleCustomerChange}
            onSearch={handleSearch}
        />
    );
}
```

## Ejemplo 3: Single Document Form

```typescript
import { CustomerPicker } from '@/components/customers/CustomerPicker';

function SingleDocumentForm() {
    const form = useForm();
    const documentType = form.watch('dte_type_id');

    return (
        <CustomerPicker
            documentType={documentType}
            defaultValues={form.getValues('customer')}
            addresses={form.watch('customer.addresses')}
            activities={form.watch('customer.activities')}
            customers={customers}
            onCustomerChange={(values) => {
                form.setValue('customer', values);
            }}
            onSearch={handleSearch}
        />
    );
}
```

## Notas Importantes

1. **El componente padre es responsable de:**
   - Hacer fetch de datos (customers, addresses, activities)
   - Manejar la búsqueda en el backend
   - Actualizar el estado del formulario padre cuando cambian los valores

2. **CustomerPicker NO:**
   - Hace fetch de datos
   - Decide qué endpoint usar
   - Filtra clientes
   - Valida datos (RHF lo hace)

3. **React Hook Form es la única fuente de verdad:**
   - Todos los valores vienen de RHF
   - No hay estado local en componentes
   - Los cambios se propagan vía `onCustomerChange`

