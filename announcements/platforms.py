# NOTE:
# - cost_model is a quick guide, not a legal/contractual statement.
# - "freemium" = some content free, advanced paths or certs paid.
# - "mixed"   = has both free and paid/subscription products.
# - offers_certificates=True means the platform issues some form of
#   certificate/badge/completion record (often paid on freemium sites).

PLATFORMS = [
    {
        "name": "Class Central",
        "home": "https://www.classcentral.com/",
        "search": "https://www.classcentral.com/search?q={q}",
        "category": "Aggregator",
        "description": "Search engine for online courses across many providers.",
        "cost_model": "free",
        "offers_certificates": False,
    },
    {
        "name": "freeCodeCamp",
        "home": "https://www.freecodecamp.org/",
        "search": "https://www.freecodecamp.org/learn/?q={q}",
        "category": "Nonprofit / Web Dev",
        "description": "Fully free coding curriculum with project-based certifications.",
        "cost_model": "free",
        "offers_certificates": True,
    },
    {
        "name": "Khan Academy",
        "home": "https://www.khanacademy.org/",
        "search": "https://www.khanacademy.org/search?page_search_query={q}",
        "category": "Nonprofit / K-12 to College",
        "description": "Free learning for math, science, computing, and more.",
        "cost_model": "free",
        "offers_certificates": False,
    },
    {
        "name": "Saylor Academy",
        "home": "https://www.saylor.org/",
        "search": "https://www.saylor.org/?s={q}",
        "category": "Nonprofit / College",
        "description": "Free self-paced college-level courses; low-cost exams and certs.",
        "cost_model": "free",
        "offers_certificates": True,
    },
    {
        "name": "Alison",
        "home": "https://alison.com/",
        "search": "https://alison.com/search/results?query={q}",
        "category": "MOOC",
        "description": "Large catalog of free courses; optional paid certificates.",
        "cost_model": "freemium",
        "offers_certificates": True,
    },
    {
        "name": "Coursera",
        "home": "https://www.coursera.org/",
        "search": "https://www.coursera.org/search?query={q}",
        "category": "MOOC / University",
        "description": "University-backed courses and professional certificates.",
        "cost_model": "mixed",  # free audit + paid certificates / subscriptions
        "offers_certificates": True,
    },
    {
        "name": "edX",
        "home": "https://www.edx.org/",
        "search": "https://www.edx.org/search?q={q}",
        "category": "MOOC / University",
        "description": "Courses from universities; MicroBachelors/MicroMasters.",
        "cost_model": "mixed",  # free audit + paid verified certs
        "offers_certificates": True,
    },
    {
        "name": "FutureLearn",
        "home": "https://www.futurelearn.com/",
        "search": "https://www.futurelearn.com/courses?query={q}",
        "category": "MOOC",
        "description": "Short courses and ExpertTracks from universities/organizations.",
        "cost_model": "freemium",
        "offers_certificates": True,
    },
    {
        "name": "Udemy",
        "home": "https://www.udemy.com/",
        "search": "https://www.udemy.com/courses/search/?q={q}",
        "category": "Marketplace",
        "description": "Instructor-created courses across all topics; frequent discounts.",
        "cost_model": "paid",  # per-course purchases (often discounted)
        "offers_certificates": True,  # completion certificates (non-accredited)
    },
    {
        "name": "Udacity",
        "home": "https://www.udacity.com/",
        "search": "https://www.udacity.com/courses/all?search={q}",
        "category": "Tech / Nanodegrees",
        "description": "Career-focused Nanodegree programs in tech fields.",
        "cost_model": "paid",
        "offers_certificates": True,
    },
    {
        "name": "Pluralsight",
        "home": "https://www.pluralsight.com/",
        "search": "https://www.pluralsight.com/search?q={q}",
        "category": "Tech",
        "description": "Tech skills with paths and assessments; strong cert-prep.",
        "cost_model": "subscription",
        "offers_certificates": True,  # completion + cert-prep badges
    },
    {
        "name": "Codecademy",
        "home": "https://www.codecademy.com/",
        "search": "https://www.codecademy.com/search?query={q}",
        "category": "Tech",
        "description": "Interactive coding lessons; Pro offers paths/certificates.",
        "cost_model": "freemium",
        "offers_certificates": True,  # with Pro
    },
    {
        "name": "LinkedIn Learning",
        "home": "https://www.linkedin.com/learning/",
        "search": "https://www.linkedin.com/learning/search?keywords={q}",
        "category": "Professional",
        "description": "Business, creative, and tech courses; add certs to profile.",
        "cost_model": "subscription",
        "offers_certificates": True,
    },
    {
        "name": "Skillshare",
        "home": "https://www.skillshare.com/",
        "search": "https://www.skillshare.com/search?query={q}",
        "category": "Creative / Marketplace",
        "description": "Creative and practical classes by creators.",
        "cost_model": "subscription",
        "offers_certificates": False,
    },
    {
        "name": "DataCamp",
        "home": "https://www.datacamp.com/",
        "search": "https://www.datacamp.com/search?q={q}",
        "category": "Data",
        "description": "Interactive data science and analytics learning.",
        "cost_model": "subscription",
        "offers_certificates": True,
    },
    {
        "name": "Google Cloud Skills Boost",
        "home": "https://www.cloudskillsboost.google/",
        "search": "https://www.cloudskillsboost.google/catalog?search={q}",
        "category": "Vendor / Cloud",
        "description": "Hands-on labs and quests for Google Cloud; cert-prep.",
        "cost_model": "mixed",  # many free labs; paid subscriptions too
        "offers_certificates": True,  # digital badges/quests
    },
    {
        "name": "Microsoft Learn",
        "home": "https://learn.microsoft.com/",
        "search": "https://learn.microsoft.com/search/?terms={q}",
        "category": "Vendor / Cloud",
        "description": "Free learning paths with badges; Microsoft cert-prep.",
        "cost_model": "free",
        "offers_certificates": True,  # badges + cert-prep
    },
    {
        "name": "AWS Training & Certification",
        "home": "https://www.aws.training/",
        "search": "https://www.aws.training/Details/Curriculum?id=20685#?phrase={q}",
        "category": "Vendor / Cloud",
        "description": "Official AWS digital training; strong certification paths.",
        "cost_model": "mixed",  # lots of free training + paid options
        "offers_certificates": True,
    },
    {
        "name": "IBM SkillsBuild",
        "home": "https://skillsbuild.org/",
        "search": "https://skillsbuild.org/search?q={q}",
        "category": "Vendor / Career",
        "description": "Free job-aligned learning with badges from IBM.",
        "cost_model": "free",
        "offers_certificates": True,
    },
    {
        "name": "MIT OpenCourseWare",
        "home": "https://ocw.mit.edu/",
        "search": "https://ocw.mit.edu/search/?q={q}",
        "category": "University / Open",
        "description": "Free MIT course materials; no enrollment or certs.",
        "cost_model": "free",
        "offers_certificates": False,
    },
    {
        "name": "Stanford Online",
        "home": "https://online.stanford.edu/",
        "search": "https://online.stanford.edu/search?search={q}",
        "category": "University",
        "description": "Professional education and free/open content from Stanford.",
        "cost_model": "mixed",
        "offers_certificates": True,
    },
    {
        "name": "OpenClassrooms",
        "home": "https://openclassrooms.com/",
        "search": "https://openclassrooms.com/en/search?q={q}",
        "category": "Career / Mentor-guided",
        "description": "Mentor-guided paths with job-ready projects and diplomas.",
        "cost_model": "subscription",
        "offers_certificates": True,
    },
]
