'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  Dumbbell, TrendingUp, Calendar, Users, Award, Clock, 
  PlayCircle, Target, Zap, BarChart3, Activity, Star,
  Download, Eye, Settings, Bell, Search, Filter
} from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { api, type Rutina, type Template } from '@/lib/api';
import { Button, Card, Badge, Input, Select } from '@/components/ui';
import { useRouter } from 'next/navigation';

interface DashboardStats {
  totalRoutines: number;
  completedWorkouts: number;
  totalExercises: number;
  activeDays: number;
  weeklyProgress: number;
  monthlyProgress: number;
  favoriteTemplates: Template[];
  recentRoutines: Rutina[];
}

export default function EnhancedDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState<'week' | 'month' | 'year'>('week');

  const loadDashboardData = useCallback(async () => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      // Load user's routines
      const routinesRes = await api.getRutinas({ usuario_id: user.id });
      const routines = routinesRes.ok ? routinesRes.data?.rutinas || [] : [];
      
      // Load popular templates
      const templatesRes = await api.getTemplates({ 
        limit: 6, 
        sort_by: 'uso_count', 
        sort_order: 'desc' 
      });
      const templates = templatesRes.ok ? templatesRes.data?.templates || [] : [];

      // Calculate stats
      const totalExercises = routines.reduce((sum, routine) => 
        sum + (routine.dias?.reduce((daySum, day) => 
          daySum + (day.ejercicios?.length || 0), 0) || 0), 0);

      const completedWorkouts = routines.reduce((sum, routine) => 
        sum + (routine.uso_count || 0), 0);

      const activeDays = routines.reduce((sum, routine) => 
        sum + (routine.dias?.length || 0), 0);

      // Mock progress data (would come from analytics API)
      const weeklyProgress = Math.floor(Math.random() * 100);
      const monthlyProgress = Math.floor(Math.random() * 100);

      setStats({
        totalRoutines: routines.length,
        completedWorkouts,
        totalExercises,
        activeDays,
        weeklyProgress,
        monthlyProgress,
        favoriteTemplates: templates.slice(0, 3),
        recentRoutines: routines.slice(0, 3)
      });
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-400">Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-400">No se pudieron cargar los datos</p>
          <Button onClick={loadDashboardData} className="mt-4">
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900/50 backdrop-blur-sm border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Dumbbell className="w-8 h-8 text-primary-500" />
              <div>
                <h1 className="text-xl font-bold text-white">Dashboard</h1>
                <p className="text-sm text-slate-400">
                  ¡Bienvenido de vuelta, {user?.nombre || 'Usuario'}!
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Buscar rutinas..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              
              <Select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as any)}
                className="w-32"
                options={[
                  { value: 'week', label: 'Semana' },
                  { value: 'month', label: 'Mes' },
                  { value: 'year', label: 'Año' }
                ]}
              />
              
              <Button variant="ghost" size="sm">
                <Bell className="w-4 h-4" />
              </Button>
              
              <Button variant="ghost" size="sm">
                <Settings className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                    <Dumbbell className="w-6 h-6 text-blue-400" />
                  </div>
                  <TrendingUp className="w-4 h-4 text-green-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-1">{stats.totalRoutines}</h3>
                <p className="text-sm text-slate-400">Rutinas Activas</p>
                <div className="mt-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span>+2 esta semana</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-500/20 rounded-lg flex items-center justify-center">
                    <Activity className="w-6 h-6 text-green-400" />
                  </div>
                  <TrendingUp className="w-4 h-4 text-green-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-1">{stats.completedWorkouts}</h3>
                <p className="text-sm text-slate-400">Entrenamientos Completados</p>
                <div className="mt-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span>+12% este mes</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center">
                    <Target className="w-6 h-6 text-purple-400" />
                  </div>
                  <TrendingUp className="w-4 h-4 text-green-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-1">{stats.totalExercises}</h3>
                <p className="text-sm text-slate-400">Ejercicios Totales</p>
                <div className="mt-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span>+8 esta semana</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                    <Calendar className="w-6 h-6 text-yellow-400" />
                  </div>
                  <Zap className="w-4 h-4 text-yellow-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-1">{stats.activeDays}</h3>
                <p className="text-sm text-slate-400">Días de Entrenamiento</p>
                <div className="mt-3">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span>5 días esta semana</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Progress Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="bg-slate-900 border-slate-800">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Progreso Semanal</h3>
                  <Badge variant="outline">Esta semana</Badge>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">Completado</span>
                      <span className="text-sm font-medium text-white">{stats.weeklyProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-primary-500 to-primary-400 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${stats.weeklyProgress}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-7 gap-2">
                    {['L', 'M', 'X', 'J', 'V', 'S', 'D'].map((day, index) => (
                      <div
                        key={index}
                        className={`aspect-square rounded-lg flex items-center justify-center text-xs font-medium ${
                          index < 5 ? 'bg-primary-500 text-white' : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {day}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card className="bg-slate-900 border-slate-800">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Progreso Mensual</h3>
                  <Badge variant="outline">Este mes</Badge>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-400">Completado</span>
                      <span className="text-sm font-medium text-white">{stats.monthlyProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-green-500 to-green-400 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${stats.monthlyProgress}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-4 gap-3">
                    <div className="text-center">
                      <div className="text-lg font-bold text-white">18</div>
                      <div className="text-xs text-slate-400">Días activos</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-white">24</div>
                      <div className="text-xs text-slate-400">Entrenamientos</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-white">156</div>
                      <div className="text-xs text-slate-400">Ejercicios</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-white">4.5</div>
                      <div className="text-xs text-slate-400">Promedio/día</div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Recent Activity & Templates */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card className="bg-slate-900 border-slate-800">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Rutinas Recientes</h3>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => router.push('/usuario/routines')}
                  >
                    Ver todas
                  </Button>
                </div>
                
                <div className="space-y-3">
                  {stats.recentRoutines.length === 0 ? (
                    <div className="text-center py-8">
                      <Dumbbell className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                      <p className="text-slate-400 text-sm">No hay rutinas recientes</p>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="mt-3"
                        onClick={() => router.push('/usuario/routines')}
                      >
                        Explorar rutinas
                      </Button>
                    </div>
                  ) : (
                    stats.recentRoutines.map((routine) => (
                      <div
                        key={routine.id}
                        className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
                        onClick={() => router.push(`/usuario/routines?routine=${routine.id}`)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-primary-500/20 rounded-lg flex items-center justify-center">
                            <Dumbbell className="w-5 h-5 text-primary-400" />
                          </div>
                          <div>
                            <h4 className="font-medium text-white">{routine.nombre}</h4>
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <span>{routine.dias?.length || 0} días</span>
                              <span>•</span>
                              <span>{routine.uso_count || 0} usos</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm">
                            <PlayCircle className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            <Card className="bg-slate-900 border-slate-800">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">Plantillas Populares</h3>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => router.push('/usuario/templates')}
                  >
                    Ver todas
                  </Button>
                </div>
                
                <div className="space-y-3">
                  {stats.favoriteTemplates.length === 0 ? (
                    <div className="text-center py-8">
                      <Star className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                      <p className="text-slate-400 text-sm">No hay plantillas disponibles</p>
                    </div>
                  ) : (
                    stats.favoriteTemplates.map((template) => (
                      <div
                        key={template.id}
                        className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
                        onClick={() => router.push(`/usuario/templates?template=${template.id}`)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                            <Star className="w-5 h-5 text-yellow-400" />
                          </div>
                          <div>
                            <h4 className="font-medium text-white">{template.nombre}</h4>
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <Badge variant="outline" size="sm">{template.categoria}</Badge>
                              <span>•</span>
                              <span>{template.uso_count} usos</span>
                              <span>•</span>
                              <div className="flex items-center gap-1">
                                <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
                                <span>{template.rating_promedio?.toFixed(1) || 'N/A'}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm">
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm">
                            <Download className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </Card>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="mt-8"
        >
          <Card className="bg-slate-900 border-slate-800">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Acciones Rápidas</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Button
                  variant="outline"
                  className="h-20 flex-col gap-2"
                  onClick={() => router.push('/usuario/routines')}
                >
                  <Dumbbell className="w-6 h-6" />
                  <span className="text-sm">Mis Rutinas</span>
                </Button>
                
                <Button
                  variant="outline"
                  className="h-20 flex-col gap-2"
                  onClick={() => router.push('/usuario/templates')}
                >
                  <Star className="w-6 h-6" />
                  <span className="text-sm">Plantillas</span>
                </Button>
                
                <Button
                  variant="outline"
                  className="h-20 flex-col gap-2"
                  onClick={() => router.push('/usuario/progress')}
                >
                  <BarChart3 className="w-6 h-6" />
                  <span className="text-sm">Progreso</span>
                </Button>
                
                <Button
                  variant="outline"
                  className="h-20 flex-col gap-2"
                  onClick={() => router.push('/usuario/settings')}
                >
                  <Settings className="w-6 h-6" />
                  <span className="text-sm">Configuración</span>
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
