# Advanced Swift & iOS Development

> The deeper 80% - advanced topics to master after learning the fundamentals.

This repository contains advanced concepts and code examples for Swift and iOS development, focusing on the sophisticated 80% of knowledge that developers typically acquire through job experience and continuous learning.

## Table of Contents

- [Advanced Swift](#advanced-swift)
- [Advanced iOS Development](#advanced-ios-development)
- [Specialized Frameworks](#specialized-frameworks)
- [App Architecture](#app-architecture)
- [App Lifecycle & Optimization](#app-lifecycle--optimization)
- [Distribution & Production](#distribution--production)
- [Resources](#resources)

## Advanced Swift

### 1. Advanced Type System

Swift offers a powerful type system with generics and type constraints:

```swift
// Generics
func swapValues<T>(_ a: inout T, _ b: inout T) {
    let temporaryA = a
    a = b
    b = temporaryA
}

// Associated Types
protocol Container {
    associatedtype Item
    mutating func add(_ item: Item)
    var count: Int { get }
}

// Type Constraints
func findIndex<T: Equatable>(of valueToFind: T, in array: [T]) -> Int? {
    for (index, value) in array.enumerated() {
        if value == valueToFind {
            return index
        }
    }
    return nil
}

// Type Erasure
struct AnyContainer<T>: Container {
    typealias Item = T
    
    private var _add: (T) -> Void
    private var _count: () -> Int
    
    init<C: Container>(_ container: C) where C.Item == T {
        _add = { container.add($0) }
        _count = { container.count }
    }
    
    mutating func add(_ item: T) {
        _add(item)
    }
    
    var count: Int {
        return _count()
    }
}
```

### 2. Memory Management

Understanding ARC and preventing memory leaks:

```swift
// Strong Reference Cycle
class Person {
    let name: String
    var apartment: Apartment?
    
    init(name: String) { self.name = name }
    deinit { print("\(name) is being deinitialized") }
}

class Apartment {
    let unit: String
    weak var tenant: Person?  // Weak reference to break cycle
    
    init(unit: String) { self.unit = unit }
    deinit { print("Apartment \(unit) is being deinitialized") }
}

// Closure Capture Lists
class ViewModel {
    var completionHandler: (() -> Void)?
    var data: [String] = []
    
    func loadData() {
        // [weak self] prevents reference cycle
        APIClient.fetchData { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let newData):
                self.data = newData
                self.completionHandler?()
            case .failure:
                break
            }
        }
    }
}
```

### 3. Advanced Concurrency

Modern approaches to handling concurrent operations:

```swift
// GCD
DispatchQueue.global(qos: .userInitiated).async {
    let result = performExpensiveCalculation()
    
    DispatchQueue.main.async {
        self.updateUI(with: result)
    }
}

// Operation Queues
let queue = OperationQueue()
queue.maxConcurrentOperationCount = 2

let operation1 = BlockOperation {
    print("Operation 1 executed")
}

let operation2 = BlockOperation {
    print("Operation 2 executed")
}

operation2.addDependency(operation1)
queue.addOperations([operation1, operation2], waitUntilFinished: false)

// Swift Concurrency (async/await)
func fetchUserData() async throws -> User {
    let data = try await URLSession.shared.data(from: userURL).0
    return try JSONDecoder().decode(User.self, from: data)
}

// Using Task
Task {
    do {
        let user = try await fetchUserData()
        updateUI(with: user)
    } catch {
        handleError(error)
    }
}

// Actor for thread safety
actor ImageCache {
    private var cache: [URL: UIImage] = [:]
    
    func image(for url: URL) -> UIImage? {
        return cache[url]
    }
    
    func insert(_ image: UIImage, for url: URL) {
        cache[url] = image
    }
}
```

### 4. Functional Programming

Advanced functional concepts and techniques:

```swift
// Higher-Order Functions
let numbers = [1, 2, 3, 4, 5]

let doubled = numbers.map { $0 * 2 }
let evenNumbers = numbers.filter { $0 % 2 == 0 }
let sum = numbers.reduce(0, +)

// Function Composition
func compose<A, B, C>(_ f: @escaping (B) -> C, _ g: @escaping (A) -> B) -> (A) -> C {
    return { f(g($0)) }
}

let addOne = { $0 + 1 }
let double = { $0 * 2 }
let addOneThenDouble = compose(double, addOne)

// Monadic Operations
extension Optional {
    func flatMap<U>(_ transform: (Wrapped) -> U?) -> U? {
        if let value = self {
            return transform(value)
        }
        return nil
    }
}

// Currying
func curriedAdd(_ a: Int) -> (Int) -> Int {
    return { b in
        return a + b
    }
}
let add5 = curriedAdd(5)
let result = add5(3)  // 8
```

## Advanced iOS Development

### 1. Advanced UI & Animations

Complex UI implementations and animations:

```swift
// Custom View Controller Transitions
class CustomTransitionDelegate: NSObject, UIViewControllerTransitioningDelegate {
    func animationController(forPresented presented: UIViewController, presenting: UIViewController, source: UIViewController) -> UIViewControllerAnimatedTransitioning? {
        return CustomPresentAnimator()
    }
    
    func animationController(forDismissed dismissed: UIViewController) -> UIViewControllerAnimatedTransitioning? {
        return CustomDismissAnimator()
    }
}

// Core Animation
let animation = CABasicAnimation(keyPath: "position.x")
animation.fromValue = view.layer.position.x
animation.toValue = view.layer.position.x + 100
animation.duration = 1
animation.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
view.layer.add(animation, forKey: "positionAnimation")

// UIKit Dynamics
let animator = UIDynamicAnimator(referenceView: view)
let gravity = UIGravityBehavior(items: [ballView])
let collision = UICollisionBehavior(items: [ballView])
collision.translatesReferenceBoundsIntoBoundary = true

animator.addBehavior(gravity)
animator.addBehavior(collision)

// Advanced SwiftUI Animations
struct AnimatedView: View {
    @State private var isExpanded = false
    
    var body: some View {
        Circle()
            .fill(Color.blue)
            .frame(width: isExpanded ? 200 : 100, height: isExpanded ? 200 : 100)
            .animation(.spring(response: 0.5, dampingFraction: 0.6), value: isExpanded)
            .onTapGesture {
                isExpanded.toggle()
            }
    }
}
```

### 2. Reactive Programming

Using Combine for reactive data flow:

```swift
// Publishers and Subscribers
let publisher = NotificationCenter.default
    .publisher(for: UIApplication.didBecomeActiveNotification)
    .map { _ in "App became active!" }

let cancellable = publisher
    .sink { string in
        print(string)
    }

// Transform operators
let stringPublisher = PassthroughSubject<String, Never>()
let subscription = stringPublisher
    .map { $0.count }
    .filter { $0 > 5 }
    .sink { count in
        print("String length: \(count)")
    }

// Combining publishers
let namePublisher = CurrentValueSubject<String, Never>("")
let agePublisher = CurrentValueSubject<Int, Never>(0)

Publishers.CombineLatest(namePublisher, agePublisher)
    .map { name, age in
        return "Name: \(name), Age: \(age)"
    }
    .sink { combined in
        print(combined)
    }
    .store(in: &cancellables)
```

### 3. Advanced Data Management

Complex persistence strategies:

```swift
// CoreData Relationships
// AppDelegate or persistent container setup
lazy var persistentContainer: NSPersistentContainer = {
    let container = NSPersistentContainer(name: "MyModel")
    container.loadPersistentStores { _, error in
        if let error = error {
            fatalError("Failed to load Core Data stack: \(error)")
        }
    }
    return container
}()

// NSFetchedResultsController for efficient table/collection views
func setupFetchedResultsController() {
    let request: NSFetchRequest<Person> = Person.fetchRequest()
    request.sortDescriptors = [NSSortDescriptor(key: "name", ascending: true)]
    
    fetchedResultsController = NSFetchedResultsController(
        fetchRequest: request,
        managedObjectContext: persistentContainer.viewContext,
        sectionNameKeyPath: nil,
        cacheName: nil
    )
    
    fetchedResultsController.delegate = self
    
    do {
        try fetchedResultsController.performFetch()
    } catch {
        print("Failed to fetch: \(error)")
    }
}

// CloudKit Integration
let container = CKContainer.default()
let privateDatabase = container.privateCloudDatabase

let record = CKRecord(recordType: "Note")
record["title"] = "My Note" as CKRecordValue
record["content"] = "This is my cloud note" as CKRecordValue

privateDatabase.save(record) { (savedRecord, error) in
    if let error = error {
        print("Error: \(error)")
    } else {
        print("Record saved successfully")
    }
}
```

## Specialized Frameworks

### 1. ARKit

Creating augmented reality experiences:

```swift
func setupARSession() {
    let configuration = ARWorldTrackingConfiguration()
    configuration.planeDetection = [.horizontal, .vertical]
    
    sceneView.session.run(configuration)
    sceneView.delegate = self
}

func renderer(_ renderer: SCNSceneRenderer, didAdd node: SCNNode, for anchor: ARAnchor) {
    guard let planeAnchor = anchor as? ARPlaneAnchor else { return }
    
    let plane = SCNPlane(width: CGFloat(planeAnchor.extent.x), 
                         height: CGFloat(planeAnchor.extent.z))
    
    let planeNode = SCNNode(geometry: plane)
    planeNode.position = SCNVector3(planeAnchor.center.x, 0, planeAnchor.center.z)
    planeNode.transform = SCNMatrix4MakeRotation(-Float.pi/2, 1, 0, 0)
    
    node.addChildNode(planeNode)
}
```

### 2. CoreML & Vision

Machine learning in iOS apps:

```swift
func classifyImage(_ image: UIImage) {
    guard let model = try? VNCoreMLModel(for: MobileNetV2().model) else {
        return
    }
    
    let request = VNCoreMLRequest(model: model) { (request, error) in
        guard let results = request.results as? [VNClassificationObservation],
              let topResult = results.first else {
            return
        }
        
        DispatchQueue.main.async {
            self.resultLabel.text = "\(topResult.identifier) - \(topResult.confidence * 100)%"
        }
    }
    
    guard let cgImage = image.cgImage else { return }
    let handler = VNImageRequestHandler(cgImage: cgImage)
    
    do {
        try handler.perform([request])
    } catch {
        print("Failed to perform classification: \(error)")
    }
}
```

### 3. Metal & Graphics

Hardware-accelerated graphics:

```swift
func setupMetal() {
    guard let device = MTLCreateSystemDefaultDevice(),
          let commandQueue = device.makeCommandQueue() else {
        return
    }
    
    self.device = device
    self.commandQueue = commandQueue
    
    // Setup Metal layer
    guard let metalLayer = CAMetalLayer() else { return }
    metalLayer.device = device
    metalLayer.pixelFormat = .bgra8Unorm
    metalLayer.framebufferOnly = true
    view.layer.addSublayer(metalLayer)
    self.metalLayer = metalLayer
}

func render() {
    guard let drawable = metalLayer.nextDrawable(),
          let commandBuffer = commandQueue.makeCommandBuffer(),
          let renderPassDescriptor = MTLRenderPassDescriptor() else {
        return
    }
    
    renderPassDescriptor.colorAttachments[0].texture = drawable.texture
    renderPassDescriptor.colorAttachments[0].loadAction = .clear
    renderPassDescriptor.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.5, 0.8, 1.0)
    
    guard let renderEncoder = commandBuffer.makeRenderCommandEncoder(descriptor: renderPassDescriptor) else {
        return
    }
    
    // Render commands go here
    renderEncoder.endEncoding()
    
    commandBuffer.present(drawable)
    commandBuffer.commit()
}
```

## App Architecture

### 1. Advanced Design Patterns

Modern architectural approaches:

```swift
// MVVM Pattern
class UserViewModel {
    // Model
    private var user: User
    
    // Published properties for the View
    @Published var displayName: String = ""
    @Published var avatarImage: UIImage?
    
    init(user: User) {
        self.user = user
        updateDisplayValues()
    }
    
    func updateUser(_ updatedUser: User) {
        self.user = updatedUser
        updateDisplayValues()
    }
    
    private func updateDisplayValues() {
        displayName = "\(user.firstName) \(user.lastName)"
        loadAvatar()
    }
    
    private func loadAvatar() {
        ImageLoader.shared.loadImage(from: user.avatarURL) { [weak self] image in
            self?.avatarImage = image
        }
    }
}

// Coordinator Pattern
protocol Coordinator: AnyObject {
    var childCoordinators: [Coordinator] { get set }
    var navigationController: UINavigationController { get set }
    
    func start()
}

class AppCoordinator: Coordinator {
    var childCoordinators = [Coordinator]()
    var navigationController: UINavigationController
    
    init(navigationController: UINavigationController) {
        self.navigationController = navigationController
    }
    
    func start() {
        let vc = HomeViewController()
        vc.coordinator = self
        navigationController.pushViewController(vc, animated: false)
    }
    
    func showLogin() {
        let loginCoordinator = LoginCoordinator(navigationController: navigationController)
        childCoordinators.append(loginCoordinator)
        loginCoordinator.start()
    }
}

// Dependency Injection
protocol NetworkServiceType {
    func fetch<T: Decodable>(endpoint: Endpoint, completion: @escaping (Result<T, Error>) -> Void)
}

class UserService {
    private let networkService: NetworkServiceType
    
    init(networkService: NetworkServiceType) {
        self.networkService = networkService
    }
    
    func fetchUserProfile(completion: @escaping (Result<UserProfile, Error>) -> Void) {
        networkService.fetch(endpoint: .userProfile) { (result: Result<UserProfile, Error>) in
            completion(result)
        }
    }
}
```

### 2. Unidirectional Data Flow

Redux and TCA-like architectures:

```swift
// Redux-inspired architecture
struct AppState {
    var counter: Int = 0
    var users: [User] = []
    var isLoading: Bool = false
}

enum Action {
    case incrementCounter
    case decrementCounter
    case loadUsers
    case usersLoaded([User])
    case setLoading(Bool)
}

typealias Reducer<State, Action> = (inout State, Action) -> Void

let appReducer: Reducer<AppState, Action> = { state, action in
    switch action {
    case .incrementCounter:
        state.counter += 1
    case .decrementCounter:
        state.counter -= 1
    case .loadUsers:
        state.isLoading = true
    case .usersLoaded(let users):
        state.users = users
        state.isLoading = false
    case .setLoading(let isLoading):
        state.isLoading = isLoading
    }
}

class Store<State, Action> {
    private var state: State
    private let reducer: Reducer<State, Action>
    private var subscribers: [(State) -> Void] = []
    
    init(initialState: State, reducer: @escaping Reducer<State, Action>) {
        self.state = initialState
        self.reducer = reducer
    }
    
    func dispatch(_ action: Action) {
        reducer(&state, action)
        subscribers.forEach { $0(state) }
    }
    
    func subscribe(onStateChanged: @escaping (State) -> Void) {
        subscribers.append(onStateChanged)
        onStateChanged(state)
    }
}
```

## App Lifecycle & Optimization

### 1. Background Processing

Working with background modes:

```swift
// Background fetch
func application(_ application: UIApplication, performFetchWithCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
    APIClient.fetchLatestData { result in
        switch result {
        case .success(let newData):
            if newData.hasChanges {
                self.processNewData(newData)
                completionHandler(.newData)
            } else {
                completionHandler(.noData)
            }
        case .failure:
            completionHandler(.failed)
        }
    }
}

// Background tasks
func scheduleAppRefresh() {
    let request = BGAppRefreshTaskRequest(identifier: "com.example.app.refresh")
    request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60) // 15 minutes from now
    
    do {
        try BGTaskScheduler.shared.submit(request)
    } catch {
        print("Could not schedule app refresh: \(error)")
    }
}

// Processing task
BGTaskScheduler.shared.register(forTaskWithIdentifier: "com.example.app.refresh", using: nil) { task in
    self.handleAppRefresh(task: task as! BGAppRefreshTask)
}

func handleAppRefresh(task: BGAppRefreshTask) {
    scheduleAppRefresh() // Schedule the next refresh
    
    let operation = APIClient.fetchLatestDataOperation()
    
    task.expirationHandler = {
        operation.cancel()
    }
    
    operation.completionBlock = {
        task.setTaskCompleted(success: !operation.isCancelled)
    }
    
    operationQueue.addOperation(operation)
}
```

### 2. Performance Optimization

Tools and techniques for improving performance:

```swift
// UICollectionView optimizations with prefetching
extension ViewController: UICollectionViewDataSourcePrefetching {
    func collectionView(_ collectionView: UICollectionView, prefetchItemsAt indexPaths: [IndexPath]) {
        for indexPath in indexPaths {
            let imageURL = imageURLs[indexPath.item]
            ImagePrefetcher.shared.prefetchImage(at: imageURL)
        }
    }
    
    func collectionView(_ collectionView: UICollectionView, cancelPrefetchingForItemsAt indexPaths: [IndexPath]) {
        for indexPath in indexPaths {
            let imageURL = imageURLs[indexPath.item]
            ImagePrefetcher.shared.cancelPrefetching(for: imageURL)
        }
    }
}

// Memory management with cache
final class ImageCache {
    private let cache = NSCache<NSString, UIImage>()
    private let lock = NSLock()
    
    static let shared = ImageCache()
    private init() {
        cache.countLimit = 100
        cache.totalCostLimit = 50 * 1024 * 1024 // 50 MB
    }
    
    func image(for key: String) -> UIImage? {
        lock.lock()
        defer { lock.unlock() }
        return cache.object(forKey: key as NSString)
    }
    
    func set(_ image: UIImage, for key: String) {
        lock.lock()
        defer { lock.unlock() }
        cache.setObject(image, forKey: key as NSString)
    }
    
    func clear() {
        lock.lock()
        defer { lock.unlock() }
        cache.removeAllObjects()
    }
}

// Time profiling
func timeFunction() {
    let start = CFAbsoluteTimeGetCurrent()
    performExpensiveOperation()
    let end = CFAbsoluteTimeGetCurrent()
    print("Operation took \(end - start) seconds")
}
```

## Distribution & Production

### 1. Continuous Integration/Deployment

Automating builds and releases:

```yaml
# Example fastlane configuration
default_platform(:ios)

platform :ios do
  desc "Run tests"
  lane :tests do
    run_tests(
      project: "MyApp.xcodeproj",
      scheme: "MyApp",
      devices: ["iPhone 11"]
    )
  end
  
  desc "Build and upload to TestFlight"
  lane :beta do
    increment_build_number
    build_app(scheme: "MyApp")
    upload_to_testflight
  end
  
  desc "Deploy to App Store"
  lane :release do
    capture_screenshots
    build_app(scheme: "MyApp")
    upload_to_app_store(
      force: true,
      submit_for_review: true
    )
  end
end
```

### 2. App Store Guidelines

Best practices for app submission:

```swift
// In-App Purchase implementation
class StoreManager {
    static let shared = StoreManager()
    private var productsRequest: SKProductsRequest?
    private var products: [SKProduct] = []
    
    func fetchProducts() {
        let productIdentifiers = Set(["com.example.app.premium"])
        productsRequest = SKProductsRequest(productIdentifiers: productIdentifiers)
        productsRequest?.delegate = self
        productsRequest?.start()
    }
    
    func purchase(product: SKProduct) {
        let payment = SKPayment(product: product)
        SKPaymentQueue.default().add(payment)
    }
}

extension StoreManager: SKProductsRequestDelegate {
    func productsRequest(_ request: SKProductsRequest, didReceive response: SKProductsResponse) {
        self.products = response.products
        NotificationCenter.default.post(name: .productsLoaded, object: products)
    }
}

// App privacy
func requestTrackingAuthorization() {
    ATTrackingManager.requestTrackingAuthorization { status in
        switch status {
        case .authorized:
            // Enable tracking features
            Analytics.setUserTrackingEnabled(true)
        case .denied, .restricted, .notDetermined:
            // Disable tracking features
            Analytics.setUserTrackingEnabled(false)
        @unknown default:
            Analytics.setUserTrackingEnabled(false)
        }
    }
}
```

## Resources

- [Advanced Swift Book](https://www.objc.io/books/advanced-swift/)
- [Swift Algorithm Club](https://github.com/raywenderlich/swift-algorithm-club)
- [Combine: Asynchronous Programming with Swift](https://www.raywenderlich.com/books/combine-asynchronous-programming-with-swift)
- [Point-Free](https://www.pointfree.co/) - Functional programming concepts
- [Swift by Sundell](https://www.swiftbysundell.com/) - Advanced Swift topics
- [iOS Dev Weekly](https://iosdevweekly.com/) - Stay updated with latest practices

## Continuous Learning

Swift and iOS development evolve rapidly. Stay current by:

1. Following WWDC sessions
2. Participating in the Swift community
3. Contributing to open source projects
4. Experimenting with new frameworks early
5. Reviewing Apple's Human Interface Guidelines regularly

## License

This repository is available under the MIT License.