'use client';

import React, { useState, useEffect } from 'react';
import { BotConfiguration, BotConfigurationCreate, BotConfigurationUpdate } from '@/lib/apiClient'; // Import types

// Define the possible bot types
type BotType = 'momentum' | 'grid' | 'dca';

interface BotFormProps {
  // Accepts either create or update data structure
  onSubmit: (formData: BotConfigurationCreate | BotConfigurationUpdate) => Promise<void>;
  initialData?: BotConfiguration; // Optional initial data for editing
}

const BotForm: React.FC<BotFormProps> = ({ onSubmit, initialData }) => {
  const [botType, setBotType] = useState<BotType>(initialData?.bot_type as BotType || 'momentum');
  const [name, setName] = useState(initialData?.name || '');
  const [symbol, setSymbol] = useState(initialData?.settings?.symbol || 'BTCUSDT');
  const [isActive, setIsActive] = useState(initialData?.is_active || false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- State for specific bot settings ---
  // Momentum
  const [rsiPeriod, setRsiPeriod] = useState(initialData?.settings?.rsi_period || 14);
  const [maShort, setMaShort] = useState(initialData?.settings?.ma_short_period || 9);
  const [maLong, setMaLong] = useState(initialData?.settings?.ma_long_period || 21);
  // Grid
  const [upperLimit, setUpperLimit] = useState(initialData?.settings?.upper_limit || '');
  const [lowerLimit, setLowerLimit] = useState(initialData?.settings?.lower_limit || '');
  const [numGrids, setNumGrids] = useState(initialData?.settings?.num_grids || 5);
  // DCA
  const [investmentAmount, setInvestmentAmount] = useState(initialData?.settings?.investment_amount || '');
  const [frequency, setFrequency] = useState(initialData?.settings?.frequency || 'daily');

  // Update state if initialData changes (e.g., navigating between edit pages)
  useEffect(() => {
    if (initialData) {
      setBotType(initialData.bot_type as BotType);
      setName(initialData.name);
      setSymbol(initialData.settings?.symbol || 'BTCUSDT');
      setIsActive(initialData.is_active);
      // Set specific settings based on type
      setRsiPeriod(initialData.settings?.rsi_period || 14);
      setMaShort(initialData.settings?.ma_short_period || 9);
      setMaLong(initialData.settings?.ma_long_period || 21);
      setUpperLimit(initialData.settings?.upper_limit || '');
      setLowerLimit(initialData.settings?.lower_limit || '');
      setNumGrids(initialData.settings?.num_grids || 5);
      setInvestmentAmount(initialData.settings?.investment_amount || '');
      setFrequency(initialData.settings?.frequency || 'daily');
    }
  }, [initialData]);


  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    let settings: Record<string, any> = { symbol: symbol.toUpperCase() };
    // Construct settings based on bot type
    if (botType === 'momentum') {
      settings = { ...settings, rsi_period: rsiPeriod, ma_short_period: maShort, ma_long_period: maLong };
      // Add other momentum settings if needed (e.g., RSI thresholds, MACD params)
    } else if (botType === 'grid') {
      settings = { ...settings, upper_limit: parseFloat(upperLimit), lower_limit: parseFloat(lowerLimit), num_grids: numGrids };
       // Add validation for limits and grids
       if (isNaN(settings.upper_limit) || isNaN(settings.lower_limit) || settings.upper_limit <= settings.lower_limit || numGrids < 2) {
           setError("Invalid grid parameters. Ensure limits are numbers, upper > lower, and grids >= 2.");
           setLoading(false);
           return;
       }
    } else if (botType === 'dca') {
      settings = { ...settings, investment_amount: parseFloat(investmentAmount), frequency: frequency };
       // Add validation
       if (isNaN(settings.investment_amount) || settings.investment_amount <= 0) {
           setError("Invalid investment amount.");
           setLoading(false);
           return;
       }
      // Add other DCA settings if implemented (smart dip, trailing stop)
    }

    const formData: BotConfigurationCreate | BotConfigurationUpdate = {
      name,
      bot_type: botType,
      settings,
      is_active: isActive,
    };

    try {
      await onSubmit(formData);
      // Success handling (e.g., redirect) is managed by the parent component
    } catch (err: any) {
      console.error("Form submission error:", err);
      setError(err.message || 'Failed to save bot configuration.');
    } finally {
      setLoading(false);
    }
  };

  // Helper to render common input fields
  const renderInputField = (id: string, label: string, type: string, value: any, onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void, required = true, placeholder?: string, step?: string) => (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>
      <input
        id={id}
        name={id}
        type={type}
        required={required}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        step={step} // For number inputs
        className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        disabled={loading}
      />
    </div>
  );

   const renderSelectField = (id: string, label: string, value: any, onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void, options: {value: string, label: string}[]) => (
     <div>
       <label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label>
       <select
         id={id}
         name={id}
         value={value}
         onChange={onChange}
         className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
         disabled={loading}
       >
         {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
       </select>
     </div>
   );

  return (
    <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded shadow">
      {/* Common Fields */}
      {renderInputField('name', 'Bot Name', 'text', name, (e) => setName(e.target.value), true, 'My Awesome Bot')}
      {renderInputField('symbol', 'Trading Symbol', 'text', symbol, (e) => setSymbol(e.target.value.toUpperCase()), true, 'BTCUSDT')}

      {/* Bot Type Selection */}
       {renderSelectField('botType', 'Bot Type', botType, (e) => setBotType(e.target.value as BotType), [
           { value: 'momentum', label: 'Momentum Bot' },
           { value: 'grid', label: 'Grid Bot' },
           { value: 'dca', label: 'DCA Bot' },
       ])}


      {/* Dynamic Fields based on Bot Type */}
      <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
        <h3 className="text-lg font-medium leading-6 text-gray-900">{botType.charAt(0).toUpperCase() + botType.slice(1)} Settings</h3>

        {botType === 'momentum' && (
          <>
            {renderInputField('rsiPeriod', 'RSI Period', 'number', rsiPeriod, (e) => setRsiPeriod(parseInt(e.target.value, 10)))}
            {renderInputField('maShort', 'Short MA Period', 'number', maShort, (e) => setMaShort(parseInt(e.target.value, 10)))}
            {renderInputField('maLong', 'Long MA Period', 'number', maLong, (e) => setMaLong(parseInt(e.target.value, 10)))}
            {/* Add fields for RSI thresholds, MACD settings if needed */}
          </>
        )}

        {botType === 'grid' && (
          <>
            {renderInputField('lowerLimit', 'Lower Price Limit', 'number', lowerLimit, (e) => setLowerLimit(e.target.value), true, 'e.g., 40000', '0.01')}
            {renderInputField('upperLimit', 'Upper Price Limit', 'number', upperLimit, (e) => setUpperLimit(e.target.value), true, 'e.g., 50000', '0.01')}
            {renderInputField('numGrids', 'Number of Grid Lines', 'number', numGrids, (e) => setNumGrids(parseInt(e.target.value, 10)), true, 'e.g., 5')}
          </>
        )}

        {botType === 'dca' && (
          <>
            {renderInputField('investmentAmount', 'Investment Amount (Quote)', 'number', investmentAmount, (e) => setInvestmentAmount(e.target.value), true, 'e.g., 100', '0.01')}
             {renderSelectField('frequency', 'Frequency', frequency, (e) => setFrequency(e.target.value), [
                 { value: 'hourly', label: 'Hourly' },
                 { value: 'daily', label: 'Daily' },
                 { value: 'weekly', label: 'Weekly' },
             ])}
            {/* Add fields for smart dip, trailing stop settings if implemented */}
          </>
        )}
      </div>

       {/* Activation Status */}
       <div className="flex items-center">
         <input
           id="isActive"
           name="isActive"
           type="checkbox"
           checked={isActive}
           onChange={(e) => setIsActive(e.target.checked)}
           disabled={loading}
           className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
         />
         <label htmlFor="isActive" className="ml-2 block text-sm text-gray-900">
           Activate Bot on Save
         </label>
       </div>


      {/* Error Display */}
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {/* Submit Button */}
      <div className="pt-5">
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => history.back()} // Simple back navigation
            disabled={loading}
            className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 mr-3"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="ml-3 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          >
            {loading ? 'Saving...' : (initialData ? 'Update Bot' : 'Create Bot')}
          </button>
        </div>
      </div>
    </form>
  );
};

export default BotForm;
