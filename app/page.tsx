import Layout from '@/components/Layout'; // Assuming components is at the root level relative to app

export default function HomePage() {
  return (
    <Layout>
      {/* This content will be placed within the Layout's main content area */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome to the Trading Dashboard
        </h1>
        <p className="mt-2 text-gray-600">
          Manage your bots and monitor market data here.
        </p>
        {/* Dashboard content will go here later */}
      </div>
    </Layout>
  );
}
