# Airtel Sandbox Testing - Quick Reference

**One-page reference for Airtel sandbox testing**

---

## 🚀 Quick Start (5 Minutes)

```bash
cd Backend

# 1. Setup credentials
python setup_airtel_credentials.py

# 2. Verify setup
python test_airtel_sandbox_setup.py

# 3. Test payments
python test_airtel_sandbox_successful.py
```

---

## 📱 Test Phone Numbers

| Number | Behavior |
|--------|----------|
| 256700000001 | ✅ Approves payment |
| 256700000002 | ❌ Insufficient funds |
| 256700000003 | ⏱️ Times out |

---

## 🔑 Environment Variables

```bash
AIRTEL_CLIENT_ID=your-client-id
AIRTEL_CLIENT_SECRET=your-client-secret
PAYMENT_ENVIRONMENT=sandbox
```

Get credentials: https://developers.airtel.africa/

---

## 🧪 Testing Scripts

| Script | Purpose |
|--------|---------|
| `setup_airtel_credentials.py` | Setup credentials |
| `test_airtel_sandbox_setup.py` | Verify configuration |
| `test_airtel_sandbox_successful.py` | Test successful payments |
| `test_airtel_sandbox_failures.py` | Test failure scenarios |

---

## ✅ Run Tests

```bash
# Manual tests
python test_airtel_sandbox_successful.py
python test_airtel_sandbox_failures.py

# Automated E2E tests
pytest Backend/payments/test_e2e_airtel_*.py -v

# All Airtel tests
pytest Backend/payments/test_*airtel*.py -v
```

---

## 🔍 Test Scenarios

- ✅ Successful payment flow
- ❌ Insufficient funds
- 🚫 User cancellation
- ⏱️ Payment timeout
- 📞 Invalid phone number
- 🔄 Payment retry
- 🔀 Provider switching

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check credentials |
| Payment doesn't complete | Normal in sandbox |
| Test numbers don't work | Check Airtel docs |
| Webhook not received | Sandbox limitation |

---

## 📚 Documentation

- **Testing Guide:** `AIRTEL_SANDBOX_TESTING_GUIDE.md`
- **Setup Guide:** `AIRTEL_SETUP_QUICK_START.md`
- **Full Guide:** `AIRTEL_MONEY_API_SETUP_GUIDE.md`

---

## 💡 Tips

- Sandbox doesn't process real money
- Test numbers don't trigger USSD prompts
- Status updates may be simulated
- Production behavior will differ
- Always test with small amounts in production

---

## 🎯 Next Steps

1. Complete sandbox testing
2. Request production credentials
3. Test with real money (small amounts)
4. Configure production webhooks
5. Go live!

---

**Need Help?** See `AIRTEL_SANDBOX_TESTING_GUIDE.md` for detailed instructions.
