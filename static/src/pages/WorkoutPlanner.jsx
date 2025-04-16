import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { 
  Calendar, 
  Dumbbell, 
  Award, 
  Clock, 
  Trash2, 
  Play, 
  PlusCircle,
  Loader,
  AlertCircle
} from 'lucide-react';

// Custom hooks and context
import { useWorkout } from '../context/WorkoutContext';

// API services
import { 
  generateWorkoutPlan, 
  getWorkoutPlans, 
  getWorkoutPlan,
  deleteWorkoutPlan,
  startWorkoutPlan,
  createExerciseSequence
} from '../services/workoutService';

/**
 * Workout Planner Page Component
 * 
 * This page allows users to:
 * 1. Generate personalized workout plans based on profile data
 * 2. View and manage saved workout plans
 * 3. Start a workout session from a selected plan
 */
const WorkoutPlanner = () => {
  const navigate = useNavigate();
  const { planId } = useParams();
  const queryClient = useQueryClient();
  const { setCurrentWorkout, setExerciseSequence } = useWorkout();
  
  // State for workout plan generation form
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    weight: 70,
    height: 175,
    gender: 'male',
    activity: 'moderate',
    goal: 'strength',
    intensity: 'medium',
    additionalRequirements: ''
  });
  
  // State for active plan details view
  const [activePlan, setActivePlan] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  
  // Query for getting all workout plans
  const { 
    data: workoutPlans,
    isLoading: plansLoading,
    error: plansError
  } = useQuery('workoutPlans', getWorkoutPlans, {
    onSuccess: (data) => {
      if (data?.plans?.length > 0 && !activePlan && !planId) {
        // Auto-select the first plan if none is active
        setActivePlan(data.plans[0]);
        setSelectedDay(data.plans[0].days?.[0] || null);
      }
    }
  });
  
  // Query for getting a specific workout plan by ID
  const {
    data: planData,
    isLoading: planLoading
  } = useQuery(
    ['workoutPlan', planId], 
    () => getWorkoutPlan(planId),
    {
      enabled: !!planId,
      onSuccess: (data) => {
        if (data?.plan) {
          setActivePlan(data.plan);
          setSelectedDay(data.plan.days?.[0] || null);
        }
      }
    }
  );
  
  // Mutation for generating a new workout plan
  const generatePlanMutation = useMutation(generateWorkoutPlan, {
    onSuccess: (data) => {
      queryClient.invalidateQueries('workoutPlans');
      setActivePlan(data.workout_plan);
      setSelectedDay(data.workout_plan?.[0] || null);
      setShowForm(false);
    }
  });
  
  // Mutation for deleting a workout plan
  const deletePlanMutation = useMutation(deleteWorkoutPlan, {
    onSuccess: () => {
      queryClient.invalidateQueries('workoutPlans');
      setActivePlan(null);
      setSelectedDay(null);
    }
  });
  
  // Mutation for starting a workout plan
  const startPlanMutation = useMutation(startWorkoutPlan, {
    onSuccess: (data) => {
      setCurrentWorkout(data.plan);
      
      // Create exercise sequence from the first day
      if (data.plan?.days?.length > 0) {
        const firstDay = data.plan.days[0];
        const sequence = createExerciseSequence(firstDay);
        setExerciseSequence(sequence);
      }
      
      // Navigate to the exercise page
      navigate('/exercise');
    }
  });
  
  // Effect to process URL parameters
  useEffect(() => {
    if (planId && workoutPlans?.plans) {
      const plan = workoutPlans.plans.find(p => p.id === parseInt(planId));
      if (plan) {
        setActivePlan(plan);
        setSelectedDay(plan.days?.[0] || null);
      }
    }
  }, [planId, workoutPlans]);
  
  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Handle form submission
  const handleFormSubmit = (e) => {
    e.preventDefault();
    
    generatePlanMutation.mutate({
      user_profile: {
        weight: parseFloat(formData.weight),
        height: parseFloat(formData.height),
        gender: formData.gender,
        activity: formData.activity,
        goal: formData.goal,
        intensity: formData.intensity
      },
      additional_requirements: formData.additionalRequirements
    });
  };
  
  // Handle plan deletion
  const handleDeletePlan = (planId) => {
    if (window.confirm('Are you sure you want to delete this workout plan?')) {
      deletePlanMutation.mutate(planId);
    }
  };
  
  // Handle plan selection for viewing
  const handleSelectPlan = (plan) => {
    setActivePlan(plan);
    setSelectedDay(plan.days?.[0] || null);
  };
  
  // Handle starting a workout from a plan
  const handleStartWorkout = (planId) => {
    startPlanMutation.mutate(planId);
  };
  
  // Get exercise icon based on type
  const getExerciseIcon = (exercise) => {
    if (exercise.is_timed) {
      return <Clock className="w-4 h-4 text-blue-500" />;
    }
    return <Dumbbell className="w-4 h-4 text-blue-500" />;
  };
  
  return (
    <div className="flex flex-col h-full">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Workout Planner</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left sidebar - Workout plan list */}
        <div className="md:col-span-1 bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-800">Your Workout Plans</h2>
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800"
            >
              <PlusCircle className="w-4 h-4 mr-1" />
              New Plan
            </button>
          </div>
          
          {plansLoading ? (
            <div className="flex items-center justify-center h-40">
              <Loader className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : plansError ? (
            <div className="flex flex-col items-center justify-center h-40 px-4 text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
              <p className="text-gray-600">Failed to load workout plans</p>
            </div>
          ) : workoutPlans?.plans?.length > 0 ? (
            <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {workoutPlans.plans.map((plan) => (
                <li key={plan.id} className={`relative ${activePlan?.id === plan.id ? 'bg-blue-50' : ''}`}>
                  <button
                    onClick={() => handleSelectPlan(plan)}
                    className="w-full text-left p-4 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900 truncate">{plan.title}</p>
                        <p className="text-xs text-gray-500">
                          Created {new Date(plan.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center">
                        <Calendar className="w-4 h-4 text-gray-500" />
                        <span className="ml-1 text-xs text-gray-500">7 days</span>
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 px-4 text-center">
              <Calendar className="w-10 h-10 text-gray-400 mb-2" />
              <p className="text-gray-600">No workout plans yet.</p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800"
              >
                Create your first plan
              </button>
            </div>
          )}
        </div>
        
        {/* Center - Plan details or form */}
        <div className="md:col-span-2">
          {showForm ? (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <h2 className="text-lg font-medium text-gray-800">Create New Workout Plan</h2>
              </div>
              
              <form onSubmit={handleFormSubmit} className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="weight" className="block text-sm font-medium text-gray-700">
                      Weight (kg)
                    </label>
                    <input
                      type="number"
                      id="weight"
                      name="weight"
                      value={formData.weight}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      required
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="height" className="block text-sm font-medium text-gray-700">
                      Height (cm)
                    </label>
                    <input
                      type="number"
                      id="height"
                      name="height"
                      value={formData.height}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      required
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="gender" className="block text-sm font-medium text-gray-700">
                      Gender
                    </label>
                    <select
                      id="gender"
                      name="gender"
                      value={formData.gender}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  
                  <div>
                    <label htmlFor="activity" className="block text-sm font-medium text-gray-700">
                      Activity Level
                    </label>
                    <select
                      id="activity"
                      name="activity"
                      value={formData.activity}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                      <option value="sedentary">Sedentary</option>
                      <option value="light">Light</option>
                      <option value="moderate">Moderate</option>
                      <option value="active">Active</option>
                      <option value="very active">Very Active</option>
                    </select>
                  </div>
                  
                  <div>
                    <label htmlFor="goal" className="block text-sm font-medium text-gray-700">
                      Fitness Goal
                    </label>
                    <select
                      id="goal"
                      name="goal"
                      value={formData.goal}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                      <option value="strength">Strength</option>
                      <option value="endurance">Endurance</option>
                      <option value="weight loss">Weight Loss</option>
                      <option value="muscle gain">Muscle Gain</option>
                      <option value="general fitness">General Fitness</option>
                    </select>
                  </div>
                  
                  <div>
                    <label htmlFor="intensity" className="block text-sm font-medium text-gray-700">
                      Desired Intensity
                    </label>
                    <select
                      id="intensity"
                      name="intensity"
                      value={formData.intensity}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                      <option value="low">Low (2-3 days/week)</option>
                      <option value="medium">Medium (3-5 days/week)</option>
                      <option value="high">High (5-7 days/week)</option>
                    </select>
                  </div>
                </div>
                
                <div>
                  <label htmlFor="additionalRequirements" className="block text-sm font-medium text-gray-700">
                    Additional Requirements (Optional)
                  </label>
                  <textarea
                    id="additionalRequirements"
                    name="additionalRequirements"
                    value={formData.additionalRequirements}
                    onChange={handleInputChange}
                    rows={3}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Any specific needs or limitations..."
                  />
                </div>
                
                <div className="flex space-x-3 justify-end">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="inline-flex justify-center py-2 px-4 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={generatePlanMutation.isLoading}
                    className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-blue-400 disabled:cursor-not-allowed"
                  >
                    {generatePlanMutation.isLoading ? (
                      <>
                        <Loader className="w-4 h-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      'Generate Plan'
                    )}
                  </button>
                </div>
              </form>
            </div>
          ) : activePlan ? (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-800">{activePlan.title}</h2>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleStartWorkout(activePlan.id)}
                    disabled={startPlanMutation.isLoading}
                    className="inline-flex items-center py-1 px-3 border border-transparent rounded-md text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-green-400 disabled:cursor-not-allowed"
                  >
                    {startPlanMutation.isLoading ? (
                      <Loader className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-1" />
                        Start Workout
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleDeletePlan(activePlan.id)}
                    disabled={deletePlanMutation.isLoading}
                    className="inline-flex items-center py-1 px-3 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:text-gray-400 disabled:cursor-not-allowed"
                  >
                    {deletePlanMutation.isLoading ? (
                      <Loader className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4 mr-1" />
                        Delete
                      </>
                    )}
                  </button>
                </div>
              </div>
              
              {/* Workout days tabs */}
              <div className="border-b border-gray-200">
                <div className="flex overflow-x-auto">
                  {activePlan.days?.map((day, index) => (
                    <button
                      key={index}
                      onClick={() => setSelectedDay(day)}
                      className={`py-2 px-4 text-sm font-medium whitespace-nowrap ${
                        selectedDay === day
                          ? 'border-b-2 border-blue-500 text-blue-600'
                          : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      {day.day}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Day exercises */}
              {selectedDay ? (
                <div className="p-4">
                  <div className="space-y-4">
                    <h3 className="text-md font-medium text-gray-900">{selectedDay.day} Exercises</h3>
                    
                    <ul className="space-y-3">
                      {selectedDay.exercises?.map((exercise, index) => (
                        <li 
                          key={index}
                          className="border border-gray-200 rounded-md p-3 bg-gray-50 flex items-center justify-between"
                        >
                          <div className="flex items-center">
                            <div className="flex-shrink-0 flex items-center justify-center h-10 w-10 rounded-md bg-blue-100 mr-3">
                              {getExerciseIcon(exercise)}
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">{exercise.name}</p>
                              <p className="text-xs text-gray-500">
                                {exercise.is_timed
                                  ? `${exercise.reps} seconds`
                                  : `${exercise.sets} sets x ${exercise.reps} reps`}
                              </p>
                            </div>
                          </div>
                          <Award className={`w-5 h-5 ${
                            index === 0 ? 'text-yellow-400' : 
                            index === 1 ? 'text-gray-400' : 
                            index === 2 ? 'text-amber-600' : 'text-transparent'
                          }`} />
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="p-4 flex items-center justify-center h-40">
                  <p className="text-gray-500">Select a day to view exercises</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <h2 className="text-lg font-medium text-gray-800">Workout Plan Details</h2>
              </div>
              <div className="p-6 flex flex-col items-center justify-center h-40">
                <Calendar className="w-12 h-12 text-gray-300 mb-2" />
                <p className="text-gray-500">Select a workout plan or create a new one</p>
                <button
                  onClick={() => setShowForm(true)}
                  className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <PlusCircle className="w-5 h-5 mr-2" />
                  Create New Plan
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkoutPlanner;