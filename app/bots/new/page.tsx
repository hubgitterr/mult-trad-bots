'use client';

import React from 'react';
import Layout from '@/components/Layout';
import BotForm from '@/components/BotForm'; // We will create this component next
import { useRouter } from 'next/navigation';
import { createBot, BotConfigurationCreate, BotConfigurationUpdate } from '@/lib/apiClient'; // Import Update type too

export default function NewBotPage() {
  const router = useRouter();

  // The BotForm onSubmit prop expects a function accepting the union type
  const handleCreateBot = async (formData: BotConfigurationCreate | BotConfigurationUpdate) => {
    try {
      // Since this is the 'new' page, we know it's a create operation.
      // We cast the formData to the specific type needed by createBot.
      const newBot = await createBot(formData as BotConfigurationCreate);
      console.log('Bot created successfully:', newBot);
      // Redirect to the main bots page after successful creation
      router.push('/bots');
      // Optionally show a success message
    } catch (error: any) {
      console.error('Failed to create bot:', error);
      // Display error message to the user on the form
      // This error handling might be better placed within the BotForm component itself
      alert(`Error creating bot: ${error.message}`);
    }
  };

  return (
    <Layout>
      <div>
        <h1 className="text-2xl font-semibold text-gray-800 mb-6">Create New Bot</h1>
        {/* Pass the creation handler to the form */}
        <BotForm onSubmit={handleCreateBot} />
      </div>
    </Layout>
  );
}
