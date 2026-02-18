"""
Candidate seeding script for RAG system.
This module contains sample candidate data and seeding logic.
"""

from agents.rag import RAGAgent, StoreRequest


CANDIDATES_DATA = [
    # Developers
    {
        "name": "John Anderson",
        "content": """
        John Anderson is a Senior Backend Developer with 6 years of experience.

        His core skills include Python, FastAPI, Django, and PostgreSQL.

        He has designed scalable REST APIs for SaaS platforms.

        Experienced with Docker, CI/CD pipelines, and AWS deployment.
        """
    },
    {
        "name": "Michael Brown",
        "content": """
        Michael Brown is a Full Stack Developer with frontend focus.

        He works with React, TypeScript, Next.js, and Tailwind CSS.

        On backend, he uses Node.js and PostgreSQL.

        Has built internal dashboards used by thousands of users.
        """
    },
    {
        "name": "Sarah Collins",
        "content": """
        Sarah Collins is a Data Engineer with 5 years of experience.

        She builds data pipelines using Python and Apache Airflow.

        Experienced with BigQuery and Snowflake.

        Strong background in ETL and data quality checks.
        """
    },
    {
        "name": "Daniel Lee",
        "content": """
        Daniel Lee is a Mobile Developer focused on cross-platform apps.

        He uses Flutter and React Native.

        Experienced with Clean Architecture and MVVM.

        Has published apps with over 50K downloads.
        """
    },
    {
        "name": "Kevin Turner",
        "content": """
        Kevin Turner is a DevOps Engineer specializing in automation.

        He uses Terraform, Docker, Kubernetes, and Helm.

        Experienced managing AWS production infrastructure.

        Strong focus on monitoring and system reliability.
        """
    },
    {
        "name": "Andrew Walker",
        "content": """
        Andrew Walker is a Backend Engineer with Go specialization.

        He builds high-performance APIs and distributed systems.

        Experienced with PostgreSQL, Redis, and Kafka.

        Strong understanding of scalability patterns.
        """
    },
    {
        "name": "Lucas Martin",
        "content": """
        Lucas Martin is a Frontend Developer focused on UX.

        He works with React, Vue.js, and modern CSS.

        Experienced optimizing web performance.

        Familiar with design systems and accessibility standards.
        """
    },
    {
        "name": "Rachel Kim",
        "content": """
        Rachel Kim is a QA Automation Engineer.

        She builds automated tests using Cypress and Playwright.

        Experienced in API testing with Postman.

        Strong advocate for testing in CI/CD pipelines.
        """
    },
    {
        "name": "Brian Scott",
        "content": """
        Brian Scott is a Software Architect.

        He designs microservices and event-driven architectures.

        Experienced with DDD and system scalability.

        Has led technical teams across multiple projects.
        """
    },
    {
        "name": "Emily Zhang",
        "content": """
        Emily Zhang is a Machine Learning Engineer.

        She builds predictive models using Python.

        Experienced with TensorFlow and PyTorch.

        Strong background in data preprocessing and evaluation.
        """
    },
    {
        "name": "Nathan Cooper",
        "content": """
        Nathan Cooper is a Cloud Engineer.

        He specializes in AWS and GCP environments.

        Experienced with infrastructure as code.

        Focused on security and cost optimization.
        """
    },
    {
        "name": "Samuel Wright",
        "content": """
        Samuel Wright is a Backend Developer.

        He uses Java and Spring Boot.

        Experienced with relational databases.

        Has built APIs for enterprise systems.
        """
    },
    {
        "name": "Oliver Reed",
        "content": """
        Oliver Reed is a Blockchain Developer.

        He works with Solidity and Ethereum.

        Experienced building smart contracts.

        Familiar with Web3 security concerns.
        """
    },
    {
        "name": "Sophia Patel",
        "content": """
        Sophia Patel is a Mobile QA Engineer.

        She tests Android and iOS applications.

        Experienced with manual and automated testing.

        Strong attention to detail.
        """
    },
    {
        "name": "William Harris",
        "content": """
        William Harris is a Legacy System Specialist.

        He maintains PHP and MySQL applications.

        Experienced refactoring old codebases.

        Focused on system stability.
        """
    },
    {
        "name": "Ethan Moore",
        "content": """
        Ethan Moore is a Game Backend Developer.

        He builds multiplayer backend services.

        Experienced with real-time systems.

        Familiar with WebSockets and scaling.
        """
    },
    {
        "name": "Jessica Long",
        "content": """
        Jessica Long is a UI Engineer.

        She builds component libraries in React.

        Experienced with Storybook.

        Strong focus on consistency and usability.
        """
    },
    {
        "name": "Aaron Mitchell",
        "content": """
        Aaron Mitchell is a Data Analyst.

        He works with SQL and Python.

        Experienced building dashboards.

        Strong understanding of business metrics.
        """
    },
    {
        "name": "Tom Bennett",
        "content": """
        Tom Bennett is a Security Engineer.

        He performs security audits.

        Experienced with penetration testing.

        Focused on application security.
        """
    },
    {
        "name": "Henry Adams",
        "content": """
        Henry Adams is an Embedded Software Engineer.

        He programs in C and C++.

        Experienced with IoT devices.

        Strong hardware-software integration skills.
        """
    },
    # More Backend Developers
    {
        "name": "Jonathan Miles",
        "content": """
        Jonathan Miles is a Backend Developer with 7 years of experience.

        He previously worked at a multinational bank as a core banking engineer.

        He developed internal transaction processing systems using Java and Spring Boot.

        Experienced handling high-volume financial data with strict compliance standards.
        """
    },
    {
        "name": "Alexandra Reed",
        "content": """
        Alexandra Reed is a Senior Software Engineer with a fintech background.

        She worked at a digital payments company handling wallet and payout systems.

        Built microservices using Python, FastAPI, and PostgreSQL.

        Experienced in PCI-DSS compliance and secure API design.
        """
    },
    {
        "name": "Benjamin Carter",
        "content": """
        Benjamin Carter is a Full Stack Developer with 5 years of experience.

        He worked at a B2B SaaS startup serving enterprise clients.

        Developed internal dashboards using React and Node.js.

        Integrated third-party APIs for billing and authentication.
        """
    },
    {
        "name": "Rachel Donovan",
        "content": """
        Rachel Donovan is a Software Engineer with experience at Google.

        She worked on internal developer productivity tools.

        Used Python and Go to build scalable backend services.

        Familiar with large-scale distributed systems.
        """
    },
    {
        "name": "Thomas Nguyen",
        "content": """
        Thomas Nguyen is a Backend Engineer specializing in fintech systems.

        He worked at a payment gateway company in Southeast Asia.

        Built settlement and reconciliation services using Go.

        Experienced handling millions of daily transactions.
        """
    },
    {
        "name": "Daniel Rodriguez",
        "content": """
        Daniel Rodriguez is a Senior Backend Developer.

        He previously worked at a regional bank.

        Designed loan management and credit scoring systems.

        Used Java, Oracle Database, and message queues.
        """
    },
    {
        "name": "Isabella Moore",
        "content": """
        Isabella Moore is a Full Stack Engineer with startup experience.

        She worked at an early-stage fintech startup.

        Built MVP products using React and Firebase.

        Closely collaborated with product and design teams.
        """
    },
    {
        "name": "Kevin O'Brien",
        "content": """
        Kevin O'Brien is a DevOps-focused Backend Engineer.

        He worked at a cloud infrastructure company.

        Built CI/CD pipelines and deployment automation.

        Experienced with Kubernetes and AWS.
        """
    },
    {
        "name": "Samuel Park",
        "content": """
        Samuel Park is a Software Engineer with experience in e-commerce platforms.

        He worked at a large online marketplace.

        Built order management and inventory services.

        Used Node.js, MongoDB, and Redis.
        """
    },
    {
        "name": "Victoria Allen",
        "content": """
        Victoria Allen is a Data Platform Engineer.

        She worked at a digital bank.

        Built data ingestion pipelines for analytics teams.

        Used Python, Airflow, and BigQuery.
        """
    },
    {
        "name": "Andrew Collins",
        "content": """
        Andrew Collins is a Senior Backend Engineer.

        He worked at a fintech lending company.

        Developed credit decision engines and scoring APIs.

        Experienced with microservices and event-driven architecture.
        """
    },
    {
        "name": "Hannah Kim",
        "content": """
        Hannah Kim is a Mobile Backend Engineer.

        She worked at a ride-hailing company.

        Built backend services supporting mobile applications.

        Used Kotlin, Spring Boot, and PostgreSQL.
        """
    },
    {
        "name": "Matthew Brooks",
        "content": """
        Matthew Brooks is a Software Engineer with enterprise experience.

        He worked at a global consulting firm.

        Built internal tools for banking clients.

        Experienced with Java, REST APIs, and system integration.
        """
    },
    {
        "name": "Olivia Turner",
        "content": """
        Olivia Turner is a Frontend Engineer with fintech exposure.

        She worked at a digital wallet company.

        Built customer-facing dashboards using React and TypeScript.

        Focused on performance and usability.
        """
    },
    {
        "name": "Christopher Young",
        "content": """
        Christopher Young is a Senior Platform Engineer.

        He worked at a cloud-native SaaS company.

        Designed shared backend services for multiple teams.

        Strong experience with Kubernetes and service meshes.
        """
    },
    {
        "name": "Nathaniel Foster",
        "content": """
        Nathaniel Foster is a Backend Developer with insurance domain experience.

        He worked at an insurtech company.

        Built policy management and claims processing systems.

        Used Python and relational databases.
        """
    },
    {
        "name": "Samantha Lee",
        "content": """
        Samantha Lee is a Junior Software Engineer.

        She started her career at a startup accelerator.

        Built internal tools and admin panels.

        Experienced with React and basic backend APIs.
        """
    },
    {
        "name": "George Mitchell",
        "content": """
        George Mitchell is a Senior Software Architect.

        He worked at a multinational bank.

        Led modernization of legacy core banking systems.

        Strong background in system design and migration strategies.
        """
    },
    {
        "name": "Evelyn Wright",
        "content": """
        Evelyn Wright is a Backend Engineer with health-tech experience.

        She worked at a healthcare SaaS company.

        Built patient data management systems.

        Focused on data privacy and compliance.
        """
    },
    {
        "name": "Lucas Fernandez",
        "content": """
        Lucas Fernandez is a Software Engineer with marketplace experience.

        He worked at a global e-commerce platform.

        Built seller management and pricing services.

        Experienced with scalable backend systems.
        """
    },
    # Marketers
    {
        "name": "Emily Watson",
        "content": """
        Emily Watson is a Digital Marketing Specialist.

        She manages Google Ads and Meta Ads campaigns.

        Experienced optimizing funnels.

        Has handled monthly budgets over $50K.
        """
    },
    {
        "name": "James Miller",
        "content": """
        James Miller is a Growth Marketer for SaaS.

        He focuses on SEO and CRO.

        Experienced using Ahrefs and Google Analytics.

        Has grown organic traffic significantly.
        """
    },
    {
        "name": "Olivia Harris",
        "content": """
        Olivia Harris is a Content Marketing Manager.

        She creates blog articles and newsletters.

        Strong understanding of buyer personas.

        Experienced collaborating with SEO teams.
        """
    },
    {
        "name": "Ryan Thompson",
        "content": """
        Ryan Thompson is a Performance Marketer.

        He runs TikTok and Facebook Ads.

        Experienced with A/B testing creatives.

        Focused on ROAS optimization.
        """
    },
    {
        "name": "Natalie Brooks",
        "content": """
        Natalie Brooks is a Brand Strategist.

        She helps startups define positioning.

        Experienced with go-to-market planning.

        Strong communication skills.
        """
    },
    {
        "name": "Chris Evans",
        "content": """
        Chris Evans is an Email Marketing Specialist.

        He builds automated email sequences.

        Experienced with Mailchimp and Klaviyo.

        Focused on open and conversion rates.
        """
    },
    {
        "name": "Laura Simmons",
        "content": """
        Laura Simmons is a Social Media Manager.

        She manages Instagram and LinkedIn accounts.

        Experienced with content calendars.

        Strong engagement optimization skills.
        """
    },
    {
        "name": "Daniel Foster",
        "content": """
        Daniel Foster is a Marketing Analyst.

        He tracks campaign performance.

        Experienced with dashboards and reporting.

        Strong data-driven mindset.
        """
    },
    {
        "name": "Rebecca Moore",
        "content": """
        Rebecca Moore is a Copywriter.

        She writes landing pages and ad copy.

        Experienced with conversion-focused writing.

        Strong storytelling skills.
        """
    },
    {
        "name": "Alex Turner",
        "content": """
        Alex Turner is a Product Marketing Manager.

        He positions products for target markets.

        Experienced launching new features.

        Strong collaboration with product teams.
        """
    },
    # Virtual Assistants
    {
        "name": "Anna Lopez",
        "content": """
        Anna Lopez is a Virtual Assistant.

        She manages emails and calendars.

        Experienced with Notion and Google Workspace.

        Strong organizational skills.
        """
    },
    {
        "name": "Maria Gonzales",
        "content": """
        Maria Gonzales is an Administrative VA.

        She supports executives remotely.

        Experienced with travel planning.

        Detail-oriented and reliable.
        """
    },
    {
        "name": "Sophia Nguyen",
        "content": """
        Sophia Nguyen is a Social Media VA.

        She schedules posts and replies.

        Experienced with Hootsuite.

        Familiar with basic analytics.
        """
    },
    {
        "name": "David Kim",
        "content": """
        David Kim is a Technical Virtual Assistant.

        He supports SaaS customer support.

        Experienced with Zendesk and Intercom.

        Strong technical understanding.
        """
    },
    {
        "name": "Laura Bennett",
        "content": """
        Laura Bennett is a General VA.

        She assists with research and reporting.

        Strong Excel and Google Sheets skills.

        Proactive and adaptable.
        """
    },
    {
        "name": "Patricia White",
        "content": """
        Patricia White is a Real Estate VA.

        She manages listings and CRM updates.

        Experienced with lead follow-ups.

        Organized and responsive.
        """
    },
    {
        "name": "Jason Miller",
        "content": """
        Jason Miller is an E-commerce VA.

        He manages product uploads.

        Experienced with Shopify.

        Handles order tracking.
        """
    },
    {
        "name": "Linda Park",
        "content": """
        Linda Park is a Finance VA.

        She handles invoicing and bookkeeping.

        Experienced with QuickBooks.

        Strong attention to detail.
        """
    },
    {
        "name": "Robert Hill",
        "content": """
        Robert Hill is a Research VA.

        He conducts market research.

        Experienced collecting competitor data.

        Strong analytical skills.
        """
    }
]


def seed_candidates():
    """Seed the database with sample candidate data."""
    agent = RAGAgent()

    print("Starting candidate seeding...")
    print("=" * 60)

    for idx, data in enumerate(CANDIDATES_DATA, 1):
        print(
            f"\n[{idx}/{len(CANDIDATES_DATA)}] Seeding candidate: {data['name']}")
        try:
            result = agent.store(StoreRequest(
                name=data['name'],
                content=data['content']
            ))
            if result.success:
                print(f"✓ Successfully stored {result.stored_chunks} chunks")
            else:
                print(f"✗ Failed: {result.message}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")

    print("\n" + "=" * 60)
    print("Candidate seeding completed!")
    print(f"Total candidates seeded: {len(CANDIDATES_DATA)}")


if __name__ == "__main__":
    seed_candidates()
