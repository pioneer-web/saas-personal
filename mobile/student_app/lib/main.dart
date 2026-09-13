import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:youtube_player_iframe/youtube_player_iframe.dart';

const bg = Color(0xFF0C0C09);
const surface = Color(0xFF1A1715);
const orange = Color(0xFFED5D26);
const muted = Color(0xFFB8B3AF);

class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8011/api/student',
  );

  static Uri uri(String path) {
    final base = apiBaseUrl.endsWith('/')
        ? apiBaseUrl.substring(0, apiBaseUrl.length - 1)
        : apiBaseUrl;
    final clean = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$base$clean');
  }
}

class SessionStore {
  static const storage = FlutterSecureStorage();
  static const key = 'student_api_token';

  Future<String?> read() => storage.read(key: key);
  Future<void> save(String token) => storage.write(key: key, value: token);
  Future<void> clear() => storage.delete(key: key);
}

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  const ApiException(this.message, {this.statusCode});
}

class ApiClient {
  final SessionStore session;
  ApiClient(this.session);

  Future<Map<String, dynamic>> login(String email, String password) async {
    return request(
      'POST',
      '/login/',
      body: {'email': email.trim(), 'password': password},
      authenticated: false,
    );
  }

  Future<Map<String, dynamic>> home() => request('GET', '/home/');
  Future<Map<String, dynamic>> history() => request('GET', '/history/');
  Future<Map<String, dynamic>> workout(Map<String, dynamic> body) =>
      request('POST', '/workout/', body: body);

  Future<void> logout() async {
    try {
      await request('POST', '/logout/', body: const {});
    } catch (_) {
      // limpa localmente mesmo se o backend estiver indisponível
    }
    await session.clear();
  }

  Future<Map<String, dynamic>> request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool authenticated = true,
  }) async {
    final headers = <String, String>{
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };

    if (authenticated) {
      final token = await session.read();
      if (token == null || token.isEmpty) {
        throw const ApiException('Sessão expirada.', statusCode: 401);
      }
      headers['Authorization'] = 'Bearer $token';
    }

    http.Response response;
    try {
      if (method == 'GET') {
        response = await http
            .get(AppConfig.uri(path), headers: headers)
            .timeout(const Duration(seconds: 20));
      } else {
        response = await http
            .post(
              AppConfig.uri(path),
              headers: headers,
              body: jsonEncode(body ?? const {}),
            )
            .timeout(const Duration(seconds: 20));
      }
    } on TimeoutException {
      throw const ApiException('Tempo de conexão esgotado.');
    } catch (_) {
      throw const ApiException('Não foi possível conectar ao servidor.');
    }

    Map<String, dynamic> data = {};
    if (response.bodyBytes.isNotEmpty) {
      try {
        final decoded = jsonDecode(utf8.decode(response.bodyBytes));
        if (decoded is Map<String, dynamic>) data = decoded;
      } catch (_) {}
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return data;
    }

    final detail = data['detail'];
    throw ApiException(
      detail is String && detail.isNotEmpty
          ? detail
          : 'Erro ${response.statusCode}.',
      statusCode: response.statusCode,
    );
  }
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const StudentApp());
}

class StudentApp extends StatefulWidget {
  const StudentApp({super.key});

  @override
  State<StudentApp> createState() => _StudentAppState();
}

class _StudentAppState extends State<StudentApp> {
  final session = SessionStore();
  late final api = ApiClient(session);
  bool checking = true;
  bool authenticated = false;

  @override
  void initState() {
    super.initState();
    checkSession();
  }

  Future<void> checkSession() async {
    final token = await session.read();
    if (!mounted) return;
    setState(() {
      authenticated = token != null && token.isNotEmpty;
      checking = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bg,
      colorScheme: ColorScheme.fromSeed(
        seedColor: orange,
        brightness: Brightness.dark,
        surface: surface,
      ),
      useMaterial3: true,
      cardTheme: const CardThemeData(color: surface, elevation: 0),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide.none,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: orange,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
    );

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Personal',
      theme: theme,
      home: checking
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : authenticated
          ? AppShell(
              api: api,
              onLogout: () => setState(() => authenticated = false),
            )
          : LoginScreen(
              api: api,
              session: session,
              onLoggedIn: () => setState(() => authenticated = true),
            ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  final ApiClient api;
  final SessionStore session;
  final VoidCallback onLoggedIn;

  const LoginScreen({
    super.key,
    required this.api,
    required this.session,
    required this.onLoggedIn,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool loading = false;
  String error = '';

  Future<void> submit() async {
    setState(() {
      loading = true;
      error = '';
    });

    try {
      final data = await widget.api.login(email.text, password.text);
      final token = data['token'];
      if (token is! String || token.isEmpty) {
        throw const ApiException('Token não recebido.');
      }
      await widget.session.save(token);
      widget.onLoggedIn();
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'PERSONAL.',
                    style: TextStyle(fontSize: 34, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Seu treino. Sua evolução.',
                    style: TextStyle(color: muted),
                  ),
                  const SizedBox(height: 34),
                  TextField(
                    controller: email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(labelText: 'E-mail'),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: password,
                    obscureText: true,
                    onSubmitted: (_) => submit(),
                    decoration: const InputDecoration(labelText: 'Senha'),
                  ),
                  if (error.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Text(
                      error,
                      style: const TextStyle(color: Colors.redAccent),
                    ),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: loading ? null : submit,
                    child: Text(loading ? 'Entrando...' : 'Entrar'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class AppShell extends StatefulWidget {
  final ApiClient api;
  final VoidCallback onLogout;

  const AppShell({super.key, required this.api, required this.onLogout});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomePage(api: widget.api),
      HistoryPage(api: widget.api),
      ProfilePage(api: widget.api, onLogout: widget.onLogout),
    ];

    return Scaffold(
      body: SafeArea(
        child: IndexedStack(index: index, children: pages),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Início',
          ),
          NavigationDestination(icon: Icon(Icons.history), label: 'Histórico'),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Perfil',
          ),
        ],
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  final ApiClient api;
  const HomePage({super.key, required this.api});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool loading = true;
  String error = '';
  Map<String, dynamic> data = {};

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() {
      loading = true;
      error = '';
    });
    try {
      final response = await widget.api.home();
      if (mounted) setState(() => data = response);
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final student = data['student'];
    final name = student is Map
        ? (student['name'] ?? 'Aluno').toString()
        : 'Aluno';
    final routines = data['routines'] is List
        ? data['routines'] as List
        : const [];
    final today = data['today_workouts'] is List
        ? data['today_workouts'] as List
        : const [];

    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Olá, $name',
            style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text('Vamos treinar?', style: TextStyle(color: muted)),
          const SizedBox(height: 22),
          if (loading)
            const Center(child: CircularProgressIndicator())
          else if (error.isNotEmpty)
            Text(error, style: const TextStyle(color: Colors.redAccent))
          else ...[
            if (today.isNotEmpty) ...[
              const Text(
                'Treino de hoje',
                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 10),
              ...today.map((item) => RoutineCard(api: widget.api, item: item)),
              const SizedBox(height: 18),
            ],
            const Text(
              'Meus treinos',
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 10),
            if (routines.isEmpty)
              const Text(
                'Nenhum treino ativo.',
                style: TextStyle(color: muted),
              ),
            ...routines.map((item) => RoutineCard(api: widget.api, item: item)),
          ],
        ],
      ),
    );
  }
}

class RoutineCard extends StatelessWidget {
  final ApiClient api;
  final dynamic item;
  const RoutineCard({super.key, required this.api, required this.item});

  @override
  Widget build(BuildContext context) {
    final map = item is Map ? item as Map : const {};
    final routineId = map['routine_id']?.toString() ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: const Icon(Icons.fitness_center, color: orange),
        title: Text(
          (map['name'] ?? 'Treino').toString(),
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text((map['plan'] ?? '').toString()),
        trailing: const Icon(Icons.chevron_right),
        onTap: routineId.isEmpty
            ? null
            : () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => WorkoutPage(api: api, routineId: routineId),
                ),
              ),
      ),
    );
  }
}

class WorkoutPage extends StatefulWidget {
  final ApiClient api;
  final String routineId;
  const WorkoutPage({super.key, required this.api, required this.routineId});

  @override
  State<WorkoutPage> createState() => _WorkoutPageState();
}

class _WorkoutPageState extends State<WorkoutPage> {
  bool loading = true;
  bool saving = false;
  String error = '';
  Map<String, dynamic> data = {};
  final Map<String, TextEditingController> reps = {};
  final Map<String, TextEditingController> loads = {};
  Timer? restTimer;
  int rest = 0;
  final Set<String> completedSets = {};

  @override
  void initState() {
    super.initState();
    detail();
  }

  @override
  void dispose() {
    restTimer?.cancel();
    for (final c in reps.values) {
      c.dispose();
    }
    for (final c in loads.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> detail() async {
    try {
      final response = await widget.api.workout({
        'action': 'detail',
        'routine_id': widget.routineId,
      });
      if (mounted) {
        setState(() {
          applyWorkoutData(response);
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> start() async {
    setState(() => saving = true);
    try {
      final response = await widget.api.workout({
        'action': 'start',
        'routine_id': widget.routineId,
      });
      if (mounted) {
        setState(() {
          applyWorkoutData(response);
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  String keyFor(String itemId, int setNumber) => '$itemId:$setNumber';

  void applyWorkoutData(Map<String, dynamic> response) {
    data = response;
    completedSets.clear();

    final rawItems = response['items'];
    if (rawItems is! List) return;

    for (final raw in rawItems) {
      if (raw is! Map) continue;

      final itemId = raw['item_id']?.toString() ?? '';
      if (itemId.isEmpty) continue;

      final completed = raw['completed_sets'];
      if (completed is! List) continue;

      for (final rawSet in completed) {
        if (rawSet is! Map) continue;

        final number = int.tryParse(rawSet['set_number']?.toString() ?? '');
        if (number == null) continue;

        completedSets.add(keyFor(itemId, number));

        final repsDone = rawSet['reps_done']?.toString() ?? '';
        if (repsDone.isNotEmpty) {
          repController(itemId, number).text = repsDone;
        }

        final loadDone = rawSet['load_kg']?.toString() ?? '';
        if (loadDone.isNotEmpty) {
          loadController(itemId, number, null).text = loadDone;
        }
      }
    }
  }

  TextEditingController repController(String itemId, int setNumber) {
    return reps.putIfAbsent(
      keyFor(itemId, setNumber),
      () => TextEditingController(),
    );
  }

  TextEditingController loadController(
    String itemId,
    int setNumber,
    dynamic initial,
  ) {
    return loads.putIfAbsent(
      keyFor(itemId, setNumber),
      () => TextEditingController(text: initial?.toString() ?? ''),
    );
  }

  Future<void> completeSet(Map item, int setNumber) async {
    final sessionId = data['session_id']?.toString() ?? '';
    final itemId = item['item_id']?.toString() ?? '';
    if (sessionId.isEmpty || itemId.isEmpty) return;

    setState(() => saving = true);
    try {
      await widget.api.workout({
        'action': 'complete_set',
        'session_id': sessionId,
        'item_id': itemId,
        'set_number': setNumber,
        'reps_done': repController(itemId, setNumber).text,
        'load_kg': loadController(itemId, setNumber, item['load_kg']).text,
      });

      if (mounted) {
        setState(() {
          completedSets.add(keyFor(itemId, setNumber));
        });
      }

      final seconds = int.tryParse(item['rest_seconds']?.toString() ?? '') ?? 0;
      if (seconds > 0) startRest(seconds);

      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Série $setNumber registrada.')));
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  void startRest(int seconds) {
    restTimer?.cancel();
    setState(() => rest = seconds);
    restTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (rest <= 1) {
        timer.cancel();
        setState(() => rest = 0);
      } else {
        setState(() => rest--);
      }
    });
  }

  Future<void> finish() async {
    final sessionId = data['session_id']?.toString() ?? '';
    if (sessionId.isEmpty) return;
    setState(() => saving = true);
    try {
      await widget.api.workout({'action': 'finish', 'session_id': sessionId});
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final routine = data['routine'] is Map ? data['routine'] as Map : const {};
    final items = data['items'] is List ? data['items'] as List : const [];
    final active = data['session_id'] != null;

    return Scaffold(
      appBar: AppBar(title: Text((routine['name'] ?? 'Treino').toString())),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          if (error.isNotEmpty) ...[
            Text(error, style: const TextStyle(color: Colors.redAccent)),
            const SizedBox(height: 12),
          ],
          if (rest > 0)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Descanso: $rest s',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
            ),
          if (!active)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: FilledButton.icon(
                onPressed: saving ? null : start,
                icon: const Icon(Icons.play_arrow),
                label: const Text('Iniciar treino'),
              ),
            ),
          ...items.map((raw) {
            if (raw is! Map) return const SizedBox();
            final item = raw;
            final itemId = item['item_id']?.toString() ?? '';
            final sets = int.tryParse(item['sets']?.toString() ?? '1') ?? 1;

            return Card(
              margin: const EdgeInsets.only(bottom: 14),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      (item['name'] ?? 'Exercício').toString(),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${item['sets']} séries · ${item['reps']} reps · ${item['rest_seconds']}s descanso',
                      style: const TextStyle(color: muted),
                    ),
                    const SizedBox(height: 14),
                    ExerciseMedia(
                      embedUrl: item['embed_url']?.toString() ?? '',
                      imageUrl: item['image_url']?.toString() ?? '',
                      externalUrl: item['video_url']?.toString() ?? '',
                    ),
                    if (active) ...[
                      const SizedBox(height: 14),
                      ...List.generate(sets, (index) {
                        final setNumber = index + 1;
                        final done = completedSets.contains(
                          keyFor(itemId, setNumber),
                        );

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 28,
                                child: Text(
                                  '$setNumber',
                                  style: TextStyle(
                                    fontWeight: FontWeight.w900,
                                    color: done
                                        ? Colors.greenAccent
                                        : Colors.white,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: TextField(
                                  controller: repController(itemId, setNumber),
                                  keyboardType: TextInputType.number,
                                  decoration: InputDecoration(
                                    labelText: 'Reps',
                                    isDense: true,
                                    filled: true,
                                    fillColor: done
                                        ? Colors.green.withValues(alpha: 0.12)
                                        : surface,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  controller: loadController(
                                    itemId,
                                    setNumber,
                                    item['load_kg'],
                                  ),
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                        decimal: true,
                                      ),
                                  decoration: InputDecoration(
                                    labelText: 'Carga kg',
                                    isDense: true,
                                    filled: true,
                                    fillColor: done
                                        ? Colors.green.withValues(alpha: 0.12)
                                        : surface,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              IconButton(
                                style: IconButton.styleFrom(
                                  backgroundColor: done
                                      ? Colors.green
                                      : Colors.white.withValues(alpha: 0.08),
                                  foregroundColor: done ? Colors.white : muted,
                                ),
                                onPressed: saving
                                    ? null
                                    : () => completeSet(item, setNumber),
                                icon: Icon(
                                  done ? Icons.check_circle : Icons.check,
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ],
                ),
              ),
            );
          }),
          if (active)
            FilledButton(
              onPressed: saving ? null : finish,
              child: const Text('Concluir treino'),
            ),
          const SizedBox(height: 30),
        ],
      ),
    );
  }
}

class ExerciseMedia extends StatefulWidget {
  final String embedUrl;
  final String imageUrl;
  final String externalUrl;

  const ExerciseMedia({
    super.key,
    required this.embedUrl,
    required this.imageUrl,
    required this.externalUrl,
  });

  @override
  State<ExerciseMedia> createState() => _ExerciseMediaState();
}

class _ExerciseMediaState extends State<ExerciseMedia> {
  YoutubePlayerController? _youtubeController;
  WebViewController? _webController;
  bool webError = false;

  @override
  void initState() {
    super.initState();

    final youtubeId = _youtubeVideoId(
      widget.externalUrl.isNotEmpty ? widget.externalUrl : widget.embedUrl,
    );

    if (youtubeId.isNotEmpty) {
      _youtubeController = YoutubePlayerController.fromVideoId(
        videoId: youtubeId,
        autoPlay: false,
        params: const YoutubePlayerParams(
          showControls: true,
          showFullscreenButton: true,
        ),
      );
      return;
    }

    final uri = Uri.tryParse(widget.embedUrl);

    if (uri != null &&
        uri.hasScheme &&
        (uri.scheme == 'https' || uri.scheme == 'http')) {
      _webController = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(surface)
        ..setNavigationDelegate(
          NavigationDelegate(
            onWebResourceError: (_) {
              if (mounted) setState(() => webError = true);
            },
          ),
        )
        ..loadRequest(uri);
    }
  }

  String _youtubeVideoId(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return '';

    final host = uri.host.toLowerCase();

    if (host == 'youtu.be') {
      return uri.pathSegments.isNotEmpty ? uri.pathSegments.first : '';
    }

    if (host.contains('youtube.com') || host.contains('youtube-nocookie.com')) {
      final queryId = uri.queryParameters['v'];
      if (queryId != null && queryId.isNotEmpty) {
        return queryId;
      }

      final segments = uri.pathSegments;
      if (segments.length >= 2 &&
          (segments[0] == 'shorts' || segments[0] == 'embed')) {
        return segments[1];
      }
    }

    return '';
  }

  Future<void> openExternal() async {
    final uri = Uri.tryParse(widget.externalUrl);
    if (uri == null) return;

    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  void dispose() {
    _youtubeController?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_youtubeController != null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: YoutubePlayer(
              controller: _youtubeController!,
              aspectRatio: 16 / 9,
            ),
          ),
          if (widget.externalUrl.isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: openExternal,
                icon: const Icon(Icons.open_in_new),
                label: const Text('Abrir vídeo'),
              ),
            ),
        ],
      );
    }

    if (_webController != null && !webError) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: WebViewWidget(controller: _webController!),
            ),
          ),
          if (widget.externalUrl.isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: openExternal,
                icon: const Icon(Icons.open_in_new),
                label: const Text('Abrir vídeo'),
              ),
            ),
        ],
      );
    }

    if (widget.imageUrl.isNotEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.network(
              widget.imageUrl,
              height: 210,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
          if (widget.externalUrl.isNotEmpty)
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: openExternal,
                icon: const Icon(Icons.play_circle_outline),
                label: const Text('Assistir vídeo'),
              ),
            ),
        ],
      );
    }

    if (widget.externalUrl.isNotEmpty) {
      return OutlinedButton.icon(
        onPressed: openExternal,
        icon: const Icon(Icons.play_circle_outline),
        label: const Text('Assistir vídeo'),
      );
    }

    return const SizedBox.shrink();
  }
}

class HistoryPage extends StatefulWidget {
  final ApiClient api;
  const HistoryPage({super.key, required this.api});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  bool loading = true;
  String error = '';
  List history = const [];

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final data = await widget.api.history();
      if (mounted) {
        setState(
          () => history = data['history'] is List
              ? data['history'] as List
              : const [],
        );
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Center(child: CircularProgressIndicator());

    return RefreshIndicator(
      onRefresh: load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Histórico',
            style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 18),
          if (error.isNotEmpty)
            Text(error, style: const TextStyle(color: Colors.redAccent))
          else if (history.isEmpty)
            const Text(
              'Nenhum treino concluído.',
              style: TextStyle(color: muted),
            )
          else
            ...history.map((raw) {
              final item = raw is Map ? raw : const {};
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  contentPadding: const EdgeInsets.all(16),
                  leading: const Icon(Icons.check_circle, color: orange),
                  title: Text(
                    (item['routine'] ?? 'Treino').toString(),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Text((item['plan'] ?? '').toString()),
                ),
              );
            }),
        ],
      ),
    );
  }
}

class ProfilePage extends StatelessWidget {
  final ApiClient api;
  final VoidCallback onLogout;
  const ProfilePage({super.key, required this.api, required this.onLogout});

  Future<void> logout() async {
    await api.logout();
    onLogout();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text(
          'Perfil',
          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 20),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Aplicativo do aluno',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Acesso protegido por token seguro.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 20),
                FilledButton.tonal(
                  onPressed: logout,
                  child: const Text('Sair'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
