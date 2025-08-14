'use client'

import { useEffect, useRef, memo } from 'react'
import * as THREE from 'three'

const AnimatedEarth = memo(() => {
  const mountRef = useRef(null)
  const sceneRef = useRef(null)
  const rendererRef = useRef(null)
  const animationIdRef = useRef(null)

  useEffect(() => {
    if (!mountRef.current) return

    // Scene setup
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    )
    camera.position.z = 2

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true 
    })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setClearColor(0x000000, 0)
    rendererRef.current = renderer

    // Earth geometry
    const geometry = new THREE.SphereGeometry(1, 64, 64)
    
    // Earth material with natural blue appearance
    const textureLoader = new THREE.TextureLoader()
    
    // Use a cleaner Earth texture without clouds
    const earthTexture = textureLoader.load('/textures/2k_earth_daymap.jpg')
    const bumpMap = textureLoader.load('/textures/2k_earth_normal_map.tif')
    const specularMap = textureLoader.load('/textures/2k_earth_specular_map.tif')
    
    // Create a natural Earth material matching the image
    const earthMaterial = new THREE.MeshPhongMaterial({
      map: earthTexture,
      bumpMap: bumpMap,
      bumpScale: 0.03, // Slightly more surface detail for realistic continents
      specularMap: specularMap,
      specular: new THREE.Color(0x4a90e2), // Natural blue specular for oceans
      shininess: 20, // Moderate shininess for realistic water reflection
      color: new THREE.Color(0xffffff) // Natural colors from texture
    })
    
    const earth = new THREE.Mesh(geometry, earthMaterial)
    scene.add(earth)
    
    // Natural lighting setup matching the image
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4) // Natural white ambient
    scene.add(ambientLight)
    
    // Main directional light from top-left (like in the image)
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2)
    directionalLight.position.set(3, 2, 3) // Top-left lighting position
    scene.add(directionalLight)
    
    // Subtle fill light from opposite side
    const fillLight = new THREE.DirectionalLight(0x4a90e2, 0.3)
    fillLight.position.set(-2, 1, -2)
    scene.add(fillLight)
    
    // Add to DOM
    mountRef.current.appendChild(renderer.domElement)
    
    // Animation loop
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)
      
      earth.rotation.y += 0.002
      
      renderer.render(scene, camera)
    }
    animate()
    
    // Handle resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', handleResize)
    
    // Cleanup
    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current)
      }
      window.removeEventListener('resize', handleResize)
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [])

  return <div ref={mountRef} className="w-full h-full" />
})

AnimatedEarth.displayName = 'AnimatedEarth'

export default AnimatedEarth 