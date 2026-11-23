# خريطة المملكة — نسخة الويب (تعمل دون إنترنت)

1. ارفع كل الملفات إلى مستودع GitHub (الجذر).
2. Settings ← Pages ← Source: **GitHub Actions**.
3. Settings ← Actions ← General ← Workflow permissions: **Read and write**.
4. Actions ← "Build offline data" ← Run workflow (يبني بيانات البحث والطرق للمملكة كاملة ولكل مدينة على حدة، ثم ينشر الموقع تلقائياً).
5. افتح الموقع، ثم الأدوات ← «بحث واتجاهات دون إنترنت»، واختر مدناً محددة أو المملكة كاملة (واي فاي).

لإضافة مدينة أو تعديل حدودها: عدّل `tools/regions.json` (id, الاسم, الحدود [غرب, جنوب, شرق, شمال]) ثم شغّل "Build offline data" من جديد.
