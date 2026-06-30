# ComplianceOS × Polkorp Integration Guide

## 📦 Standalone HTML Embed

ComplianceOS is now available as a standalone HTML page (`compliance-os-embed.html`) that can be embedded directly into the Polkorp website with zero dependencies.

## 🚀 Quick Integration

### Option 1: Direct Embed (Recommended)

Copy the HTML file to your Polkorp public directory:

```bash
cp frontend/compliance-os-embed.html /path/to/polkorp/public/compliance-assessment.html
```

Then link to it from Polkorp:

```html
<!-- In your Polkorp navigation/menu -->
<a href="https://polkorp.com/compliance-assessment.html">Compliance Assessment</a>

<!-- Or embed in an iframe -->
<iframe 
  src="https://polkorp.com/compliance-assessment.html" 
  width="100%" 
  height="800px"
  frameborder="0"
  style="border: none; border-radius: 8px;"
></iframe>
```

### Option 2: Docker-Based Deployment

If you want a dedicated microservice:

```bash
# Serve just the HTML via lightweight web server
docker run -d \
  -p 3001:80 \
  -v $(pwd)/frontend/compliance-os-embed.html:/usr/share/nginx/html/index.html \
  -e TZ=America/Buenos_Aires \
  nginx:alpine
```

Then access at: `http://localhost:3001`

### Option 3: Next.js Integration (Production)

Add to your Polkorp Next.js app:

```bash
# Copy component to Polkorp codebase
cp frontend/app/components/AssessmentPanel.tsx ../polkorp/app/components/
cp frontend/app/entities/page.tsx ../polkorp/app/compliance/
```

Then in your Polkorp page:

```tsx
// app/compliance/page.tsx
import { AssessmentPanel } from '@/components/AssessmentPanel'

export default function CompliancePage() {
  return (
    <div className="min-h-screen bg-background p-8">
      <h1>Entity Compliance Assessment</h1>
      <AssessmentPanel 
        tenantId="polkorp"
        entityId=""
        entityType="fintech"
        sectors={['payments']}
      />
    </div>
  )
}
```

## ⚙️ Configuration

### Update API Endpoint

In `compliance-os-embed.html`, change line ~280:

```javascript
const API_URL = 'http://localhost:8000'; // Local development

// Change to production:
const API_URL = 'https://api.polkorp.com'; // Production
// or
const API_URL = 'https://compliance-api.example.com'; // Dedicated API server
```

### Environment Variables

Create `.env.production` for production deployment:

```env
NEXT_PUBLIC_API_URL=https://api.polkorp.com
NEXT_PUBLIC_TENANT_ID=polkorp
```

## 🔗 API Requirements

The HTML embed requires these endpoints running:

```
POST   /api/v1/agents/assess              (with X-Tenant-Id header)
GET    /api/v1/agents/registry            (optional, for agent discovery)
GET    /api/v1/agents/capabilities        (optional)
```

### CORS Configuration

Update your backend `app/core/config.py` to allow Polkorp domain:

```python
CORS_ORIGINS = [
    "https://polkorp.com",
    "https://www.polkorp.com",
    "https://compliance.polkorp.com",
    "http://localhost:3000",  # dev
]
```

## 📱 Polkorp Navigation Integration

### Example 1: Dedicated Page

```html
<!-- In Polkorp header/nav -->
<nav>
  <a href="/">Home</a>
  <a href="/services">Services</a>
  <a href="/compliance">Compliance Assessment</a>  <!-- NEW -->
  <a href="/about">About</a>
</nav>

<!-- In pages/compliance.html or compliance/page.tsx -->
<iframe 
  src="/compliance-assessment.html" 
  style="width: 100%; height: calc(100vh - 200px); border: none;"
/>
```

### Example 2: Embedded in Dashboard

```html
<!-- In polkorp/dashboard/page.tsx or similar -->
<div className="dashboard-grid">
  <div className="widget">
    <h2>Compliance Status</h2>
    <iframe 
      src="/compliance-assessment.html" 
      className="compliance-widget"
    />
  </div>
</div>
```

### Example 3: Modal/Popup

```html
<button onclick="openComplianceModal()">Check Compliance</button>

<dialog id="complianceModal" style="width: 90vw; max-width: 1200px;">
  <button onclick="document.getElementById('complianceModal').close()">Close</button>
  <iframe 
    src="/compliance-assessment.html"
    style="width: 100%; height: 80vh; border: none;"
  />
</dialog>

<script>
  function openComplianceModal() {
    document.getElementById('complianceModal').showModal();
  }
</script>
```

## 🎨 Styling Customization

The HTML includes Tailwind-like CSS. To match Polkorp's design:

1. Extract CSS variables from lines 1-350
2. Override colors in your Polkorp stylesheet:

```css
/* Override ComplianceOS colors */
:root {
  --compliance-primary: #your-primary-color;
  --compliance-bg: #your-bg-color;
  --compliance-text: #your-text-color;
}
```

Or modify the HTML directly:

```html
<style>
  /* Change primary color from #3b82f6 (blue) to Polkorp brand color */
  .btn, .badge, .score-card {
    --primary: #your-brand-color;
  }
</style>
```

## 🔐 Security Considerations

### 1. Authentication
The HTML embed expects JWT tokens in localStorage:

```javascript
// In Polkorp auth flow, store token after login:
localStorage.setItem('auth_token', jwtToken);
```

The embed automatically includes it in the `Authorization` header:

```javascript
headers: {
  'Authorization': `Bearer ${token}`,
  'X-Tenant-Id': 'polkorp'
}
```

### 2. Multi-Tenant Isolation
Always set the correct tenant ID:

```javascript
// For Polkorp:
document.getElementById('tenantId').value = 'polkorp';

// For other tenants in a multi-tenant Polkorp instance:
document.getElementById('tenantId').value = getUserTenantId();
```

### 3. HTTPS in Production
Ensure API is served over HTTPS:

```javascript
const API_URL = 'https://api.polkorp.com'; // Always HTTPS
```

## 📊 Usage Examples

### Example 1: Polkorp Customer Portal

```html
<!-- polkorp/portal/compliance.html -->
<div class="portal-layout">
  <header>
    <h1>Your Compliance Dashboard</h1>
    <p>Powered by ComplianceOS</p>
  </header>
  
  <main>
    <iframe 
      src="/compliance-assessment.html"
      style="width: 100%; height: 800px;"
    />
  </main>
  
  <footer>
    <p>© 2026 Polkorp. Compliance data is confidential.</p>
  </footer>
</div>
```

### Example 2: Polkorp Admin Dashboard

```jsx
// admin/compliance-batch.tsx
import ComplianceEmbed from '@/components/ComplianceEmbed'

export default function AdminCompliance() {
  const entities = useQuery(`/api/entities`); // Your DB
  
  return (
    <div>
      <h1>Bulk Compliance Assessment</h1>
      
      {entities.map(entity => (
        <div key={entity.id}>
          <h2>{entity.name}</h2>
          <iframe 
            src={`/compliance-assessment.html?entity=${entity.id}`}
          />
        </div>
      ))}
    </div>
  )
}
```

## 📈 Advanced Features

### Pre-fill Entity ID

```html
<iframe 
  src="/compliance-assessment.html?entity=corp-123&tenant=polkorp"
/>
```

Then in the HTML, add query param parsing:

```javascript
// Add this after line 280 in the script section:
const params = new URLSearchParams(window.location.search);
document.getElementById('entityId').value = params.get('entity') || '';
document.getElementById('tenantId').value = params.get('tenant') || 'polkorp';
```

### Custom Callback

```javascript
// In Polkorp page, add this after iframe:
window.addEventListener('message', (event) => {
  if (event.data.type === 'complianceAssessmentComplete') {
    console.log('Assessment complete:', event.data.result);
    // Handle result in Polkorp app
  }
});
```

## 🚨 Troubleshooting

### CORS Error
```
Access to fetch at 'http://...' from origin 'https://...' has been blocked
```

Solution: Add to backend `config.py`:
```python
CORS_ORIGINS = ["https://polkorp.com", "http://localhost:3000"]
```

### API Timeout
```
Error: Assessment failed
```

Solution: Increase backend timeout in `docker-compose.yml`:
```yaml
environment:
  - TIMEOUT=300  # 5 minutes
```

### Iframe Not Loading
Make sure `X-Frame-Options` is not set to `DENY`:

```python
# In FastAPI middleware
response.headers["X-Frame-Options"] = "SAMEORIGIN"
```

## 📝 Deployment Checklist

- [ ] Copy `compliance-os-embed.html` to Polkorp public directory
- [ ] Update `API_URL` in HTML to production backend
- [ ] Configure CORS in backend for Polkorp domain
- [ ] Test in development environment
- [ ] Set up HTTPS for production
- [ ] Store JWT tokens in localStorage
- [ ] Test multi-tenant isolation
- [ ] Update Polkorp navigation/menu
- [ ] Add to Polkorp footer links
- [ ] Monitor API logs for errors
- [ ] Set up alerts for rate limiting (429 responses)

## 🎯 Next Steps

1. **Test locally**: Open `compliance-os-embed.html` in browser with `http://localhost:8000` backend
2. **Deploy backend**: Run ComplianceOS on production server
3. **Host HTML**: Copy to Polkorp's web server
4. **Wire navigation**: Add link/button to Polkorp site
5. **Monitor**: Watch logs for assessment requests

## 📞 Support

For issues or questions:
- Check `API_GUIDE.md` for endpoint details
- Review `ARCHITECTURE.md` for agent framework info
- See `CLAUDE.md` for security/config requirements

---

**ComplianceOS HTML Embed v1.0** • Ready for production deployment on Polkorp
